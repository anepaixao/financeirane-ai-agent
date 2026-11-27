from dataclasses import FrozenInstanceError
from datetime import date
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

import financeirane.repositories.receitas_previstas as modulo_repositorio
from financeirane.domain.compromissos import (
    CompromissoFinanceiro,
    StatusCompromisso,
    TipoCompromisso,
)
from financeirane.domain.exceptions import EntradaInvalidaError, FinanceiraneError
from financeirane.domain.receitas_previstas import ReceitaPrevista, StatusReceita
from financeirane.repositories.compromissos import RepositorioCompromissosEmMemoria
from financeirane.repositories.receitas_previstas import (
    ReceitaPrevistaIdentificada,
    ReceitaPrevistaNaoEncontradaError,
    RepositorioReceitasPrevistas,
    RepositorioReceitasPrevistasEmMemoria,
)


def criar_receita(**alteracoes):
    dados = {
        "descricao": "Salário",
        "valor": Decimal("1700.00"),
        "data_prevista": date(2026, 12, 7),
        "status": StatusReceita.PREVISTA,
    }
    dados.update(alteracoes)
    return ReceitaPrevista(**dados)


def test_repositorio_em_memoria_satisfaz_contrato():
    repositorio: RepositorioReceitasPrevistas = RepositorioReceitasPrevistasEmMemoria()

    assert repositorio.listar() == []
    salva = repositorio.salvar(criar_receita())
    assert repositorio.buscar(salva.identificador) == salva
    assert repositorio.atualizar(salva.identificador, criar_receita()) == salva


def test_salvar_e_buscar_preservam_receita_e_uuid():
    repositorio = RepositorioReceitasPrevistasEmMemoria()
    receita = criar_receita()

    salva = repositorio.salvar(receita)

    assert isinstance(salva, ReceitaPrevistaIdentificada)
    assert isinstance(salva.identificador, UUID)
    assert salva.receita is receita
    assert repositorio.buscar(salva.identificador) == salva
    assert not hasattr(receita, "identificador")


def test_salvar_mesma_instancia_cria_ocorrencias_distintas():
    repositorio = RepositorioReceitasPrevistasEmMemoria()
    receita = criar_receita()

    primeira = repositorio.salvar(receita)
    segunda = repositorio.salvar(receita)

    assert primeira.identificador != segunda.identificador
    assert primeira.receita is segunda.receita
    assert repositorio.listar() == [primeira, segunda]


def test_receitas_distintas_com_dados_iguais_podem_ser_salvas():
    repositorio = RepositorioReceitasPrevistasEmMemoria()

    primeira = repositorio.salvar(criar_receita())
    segunda = repositorio.salvar(criar_receita())

    assert primeira.identificador != segunda.identificador
    assert primeira.receita == segunda.receita
    assert primeira.receita is not segunda.receita


def test_salvar_gera_outro_uuid_ao_encontrar_colisao(monkeypatch):
    repositorio = RepositorioReceitasPrevistasEmMemoria()
    primeiro_id = UUID(int=1)
    segundo_id = UUID(int=2)
    ids = iter((primeiro_id, primeiro_id, segundo_id))
    monkeypatch.setattr(modulo_repositorio, "uuid4", lambda: next(ids))

    primeira = repositorio.salvar(criar_receita())
    segunda = repositorio.salvar(criar_receita(descricao="Freelance"))

    assert primeira.identificador == primeiro_id
    assert segunda.identificador == segundo_id
    assert repositorio.listar() == [primeira, segunda]


def test_listar_retorna_snapshot_em_ordem_de_insercao():
    repositorio = RepositorioReceitasPrevistasEmMemoria()
    primeira = repositorio.salvar(criar_receita())
    segunda = repositorio.salvar(criar_receita(descricao="Freelance"))

    lista = repositorio.listar()
    lista.clear()

    assert repositorio.listar() == [primeira, segunda]


def test_listar_snapshot_nao_muda_apos_atualizacao():
    repositorio = RepositorioReceitasPrevistasEmMemoria()
    original = repositorio.salvar(criar_receita())
    snapshot = repositorio.listar()

    atualizada = repositorio.atualizar(
        original.identificador, criar_receita(valor="1800.00")
    )

    assert snapshot == [original]
    assert repositorio.listar() == [atualizada]


def test_buscar_uuid_inexistente_lanca_erro_explicito():
    repositorio = RepositorioReceitasPrevistasEmMemoria()

    with pytest.raises(ReceitaPrevistaNaoEncontradaError, match="não encontrada"):
        repositorio.buscar(uuid4())


def test_erro_de_nao_encontrada_pertence_a_hierarquia_existente():
    assert issubclass(ReceitaPrevistaNaoEncontradaError, FinanceiraneError)


@pytest.mark.parametrize("identificador", [None, "id", 123, []])
def test_buscar_rejeita_identificador_invalido(identificador):
    repositorio = RepositorioReceitasPrevistasEmMemoria()

    with pytest.raises(EntradaInvalidaError, match="Identificador"):
        repositorio.buscar(identificador)


def test_atualizar_preserva_uuid_e_substitui_receita():
    repositorio = RepositorioReceitasPrevistasEmMemoria()
    original = criar_receita()
    salva = repositorio.salvar(original)
    nova = criar_receita(valor="1900.00", data_prevista=date(2027, 1, 7))

    resultado = repositorio.atualizar(salva.identificador, nova)

    assert resultado.identificador == salva.identificador
    assert resultado.receita is nova
    assert repositorio.buscar(salva.identificador) == resultado
    assert repositorio.listar() == [resultado]
    assert original.valor == Decimal("1700.00")


def test_atualizar_uuid_inexistente_preserva_dados():
    repositorio = RepositorioReceitasPrevistasEmMemoria()
    salva = repositorio.salvar(criar_receita())

    with pytest.raises(ReceitaPrevistaNaoEncontradaError, match="não encontrada"):
        repositorio.atualizar(uuid4(), criar_receita(valor="1900.00"))

    assert repositorio.listar() == [salva]


@pytest.mark.parametrize("identificador", [None, "id", 123, []])
def test_atualizar_rejeita_identificador_invalido(identificador):
    repositorio = RepositorioReceitasPrevistasEmMemoria()
    salva = repositorio.salvar(criar_receita())

    with pytest.raises(EntradaInvalidaError, match="Identificador"):
        repositorio.atualizar(identificador, criar_receita(valor="1900.00"))

    assert repositorio.listar() == [salva]


@pytest.mark.parametrize("receita", [None, {}, "receita"])
def test_salvar_rejeita_objeto_invalido_sem_criar_registro(receita):
    repositorio = RepositorioReceitasPrevistasEmMemoria()

    with pytest.raises(EntradaInvalidaError, match="Receita prevista inválida"):
        repositorio.salvar(receita)

    assert repositorio.listar() == []


@pytest.mark.parametrize("receita", [None, {}, "receita"])
def test_atualizar_rejeita_objeto_invalido_sem_substituir(receita):
    repositorio = RepositorioReceitasPrevistasEmMemoria()
    salva = repositorio.salvar(criar_receita())

    with pytest.raises(EntradaInvalidaError, match="Receita prevista inválida"):
        repositorio.atualizar(salva.identificador, receita)

    assert repositorio.buscar(salva.identificador) == salva


def test_validacao_do_dominio_impede_salvar_valor_ou_data_invalidos():
    repositorio = RepositorioReceitasPrevistasEmMemoria()

    with pytest.raises(EntradaInvalidaError):
        repositorio.salvar(criar_receita(valor=0))
    with pytest.raises(EntradaInvalidaError):
        repositorio.salvar(criar_receita(data_prevista="31/02/2026"))

    assert repositorio.listar() == []


def test_atualizar_usa_uuid_sem_depender_da_instancia():
    repositorio = RepositorioReceitasPrevistasEmMemoria()
    primeira = repositorio.salvar(criar_receita())
    segunda = repositorio.salvar(criar_receita(descricao="Freelance"))

    atualizada = repositorio.atualizar(segunda.identificador, primeira.receita)

    assert atualizada.identificador == segunda.identificador
    assert atualizada.receita is primeira.receita
    assert repositorio.buscar(primeira.identificador) == primeira
    assert repositorio.buscar(segunda.identificador) == atualizada
    assert repositorio.listar() == [primeira, atualizada]


def test_criar_atualizar_e_salvar_novamente_preserva_ids_distintos():
    repositorio = RepositorioReceitasPrevistasEmMemoria()
    original = criar_receita()

    criada = repositorio.salvar(original)
    nova = criar_receita(valor="1900.00")
    atualizada = repositorio.atualizar(criada.identificador, nova)
    outra = repositorio.salvar(nova)

    assert atualizada.identificador == criada.identificador
    assert outra.identificador != criada.identificador
    assert repositorio.listar() == [atualizada, outra]


def test_modelo_de_receita_permanece_imutavel():
    receita = criar_receita()
    repositorio = RepositorioReceitasPrevistasEmMemoria()
    repositorio.salvar(receita)

    with pytest.raises(FrozenInstanceError):
        receita.valor = Decimal("1900.00")


def test_repositorio_de_compromissos_continua_independente():
    compromissos = RepositorioCompromissosEmMemoria()
    receitas = RepositorioReceitasPrevistasEmMemoria()
    compromisso = CompromissoFinanceiro(
        descricao="Internet",
        valor=Decimal("89.90"),
        vencimento=date(2026, 12, 10),
        tipo=TipoCompromisso.CONTA,
        status=StatusCompromisso.PENDENTE,
    )

    salvo = compromissos.salvar(compromisso)
    receitas.salvar(criar_receita())

    assert compromissos.listar() == [salvo]
    assert len(receitas.listar()) == 1
