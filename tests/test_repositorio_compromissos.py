from datetime import date
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

import financeirane.repositories.compromissos as modulo_repositorio
from financeirane.domain.compromissos import (
    CompromissoFinanceiro,
    StatusCompromisso,
    TipoCompromisso,
)
from financeirane.domain.exceptions import EntradaInvalidaError
from financeirane.repositories.compromissos import (
    CompromissoNaoEncontradoError,
    RepositorioCompromissos,
    RepositorioCompromissosEmMemoria,
)


def criar_compromisso(**alteracoes):
    dados = {
        "descricao": "Internet",
        "valor": Decimal("89.90"),
        "vencimento": date(2026, 12, 10),
        "tipo": TipoCompromisso.CONTA,
        "status": StatusCompromisso.PENDENTE,
    }
    dados.update(alteracoes)
    return CompromissoFinanceiro(**dados)


def test_repositorio_em_memoria_satisfaz_contrato():
    repositorio: RepositorioCompromissos = RepositorioCompromissosEmMemoria()

    assert repositorio.listar() == []


def test_salvar_e_buscar_preservam_compromisso_e_identificador():
    repositorio = RepositorioCompromissosEmMemoria()
    compromisso = criar_compromisso()

    salvo = repositorio.salvar(compromisso)

    assert isinstance(salvo.identificador, UUID)
    assert salvo.compromisso is compromisso
    assert repositorio.buscar(salvo.identificador) == salvo


def test_salvar_mesma_instancia_cria_dois_registros_independentes():
    repositorio = RepositorioCompromissosEmMemoria()
    compromisso = criar_compromisso()

    primeiro = repositorio.salvar(compromisso)
    segundo = repositorio.salvar(compromisso)

    assert segundo.identificador != primeiro.identificador
    assert segundo.compromisso is primeiro.compromisso
    assert repositorio.listar() == [primeiro, segundo]


def test_compromissos_distintos_com_mesmos_dados_podem_ser_salvos():
    repositorio = RepositorioCompromissosEmMemoria()

    primeiro = repositorio.salvar(criar_compromisso())
    segundo = repositorio.salvar(criar_compromisso())

    assert primeiro.identificador != segundo.identificador
    assert primeiro.compromisso == segundo.compromisso
    assert len(repositorio.listar()) == 2


def test_salvar_gera_outro_uuid_se_ocorrer_colisao(monkeypatch):
    repositorio = RepositorioCompromissosEmMemoria()
    primeiro_id = UUID(int=1)
    segundo_id = UUID(int=2)
    ids = iter((primeiro_id, primeiro_id, segundo_id))
    monkeypatch.setattr(modulo_repositorio, "uuid4", lambda: next(ids))

    primeiro = repositorio.salvar(criar_compromisso())
    segundo = repositorio.salvar(criar_compromisso())

    assert primeiro.identificador == primeiro_id
    assert segundo.identificador == segundo_id


def test_listar_retorna_snapshot_em_ordem_de_insercao():
    repositorio = RepositorioCompromissosEmMemoria()
    primeiro = repositorio.salvar(criar_compromisso())
    segundo = repositorio.salvar(criar_compromisso(descricao="Aluguel"))

    lista = repositorio.listar()
    lista.clear()

    assert repositorio.listar() == [primeiro, segundo]


def test_buscar_identificador_inexistente_lanca_erro_explicito():
    repositorio = RepositorioCompromissosEmMemoria()

    with pytest.raises(CompromissoNaoEncontradoError, match="não encontrado"):
        repositorio.buscar(uuid4())


@pytest.mark.parametrize("identificador", [None, "id", 123, []])
def test_buscar_rejeita_identificador_invalido(identificador):
    repositorio = RepositorioCompromissosEmMemoria()

    with pytest.raises(EntradaInvalidaError, match="Identificador"):
        repositorio.buscar(identificador)


def test_atualizar_preserva_identificador_e_substitui_objeto():
    repositorio = RepositorioCompromissosEmMemoria()
    original = criar_compromisso()
    salvo = repositorio.salvar(original)
    atualizado = original.atualizar(valor="100.00").marcar_como_pago()

    resultado = repositorio.atualizar(salvo.identificador, atualizado)

    assert resultado.identificador == salvo.identificador
    assert resultado.compromisso is atualizado
    assert repositorio.buscar(salvo.identificador) == resultado
    assert repositorio.listar() == [resultado]
    assert original.valor == Decimal("89.90")
    assert original.status is StatusCompromisso.PENDENTE


def test_atualizar_identificador_inexistente_lanca_erro_explicito():
    repositorio = RepositorioCompromissosEmMemoria()

    with pytest.raises(CompromissoNaoEncontradoError, match="não encontrado"):
        repositorio.atualizar(uuid4(), criar_compromisso())


@pytest.mark.parametrize("identificador", [None, "id", 123, []])
def test_atualizar_rejeita_identificador_invalido(identificador):
    repositorio = RepositorioCompromissosEmMemoria()

    with pytest.raises(EntradaInvalidaError, match="Identificador"):
        repositorio.atualizar(identificador, criar_compromisso())


@pytest.mark.parametrize("compromisso", [None, {}, "compromisso"])
def test_salvar_rejeita_objeto_que_nao_seja_do_dominio(compromisso):
    repositorio = RepositorioCompromissosEmMemoria()

    with pytest.raises(EntradaInvalidaError, match="Compromisso financeiro"):
        repositorio.salvar(compromisso)

    assert repositorio.listar() == []


def test_atualizar_rejeita_objeto_invalido_sem_substituir_o_existente():
    repositorio = RepositorioCompromissosEmMemoria()
    salvo = repositorio.salvar(criar_compromisso())

    with pytest.raises(EntradaInvalidaError, match="Compromisso financeiro"):
        repositorio.atualizar(salvo.identificador, {"valor": 0})

    assert repositorio.buscar(salvo.identificador) == salvo


def test_validacao_do_dominio_impede_salvar_valor_ou_data_invalidos():
    repositorio = RepositorioCompromissosEmMemoria()

    with pytest.raises(EntradaInvalidaError):
        repositorio.salvar(criar_compromisso(valor=0))
    with pytest.raises(EntradaInvalidaError):
        repositorio.salvar(criar_compromisso(vencimento="31/02/2026"))

    assert repositorio.listar() == []


def test_atualizar_usa_identificador_sem_depender_da_instancia():
    repositorio = RepositorioCompromissosEmMemoria()
    primeiro = repositorio.salvar(criar_compromisso())
    segundo = repositorio.salvar(criar_compromisso(descricao="Aluguel"))

    atualizado = repositorio.atualizar(segundo.identificador, primeiro.compromisso)

    assert atualizado.identificador == segundo.identificador
    assert atualizado.compromisso is primeiro.compromisso
    assert repositorio.buscar(primeiro.identificador) == primeiro
    assert repositorio.buscar(segundo.identificador) == atualizado


def test_criar_atualizar_e_salvar_novamente_preserva_ids_distintos():
    repositorio = RepositorioCompromissosEmMemoria()
    original = criar_compromisso()

    criado = repositorio.salvar(original)
    alterado = original.atualizar(valor="100.00").marcar_como_pago()
    atualizado = repositorio.atualizar(criado.identificador, alterado)
    novo = repositorio.salvar(alterado)

    assert atualizado.identificador == criado.identificador
    assert repositorio.buscar(criado.identificador) == atualizado
    assert novo.identificador != criado.identificador
    assert repositorio.listar() == [atualizado, novo]
