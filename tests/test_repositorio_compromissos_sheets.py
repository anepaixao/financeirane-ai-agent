from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import UUID

import pytest
from gspread.exceptions import WorksheetNotFound
from requests.exceptions import Timeout

import financeirane.repositories.compromissos_sheets as modulo_sheets
from financeirane.domain.compromissos import (
    CompromissoFinanceiro,
    StatusCompromisso,
    TipoCompromisso,
)
from financeirane.domain.exceptions import EntradaInvalidaError
from financeirane.repositories.compromissos import CompromissoNaoEncontradoError
from financeirane.repositories.compromissos_sheets import (
    CABECALHO,
    CompromissoDuplicadoError,
    CriacaoIndeterminadaError,
    DadosCompromissosInvalidosError,
    RepositorioCompromissosSheets,
    RepositorioSheetsEscritaError,
    RepositorioSheetsLeituraError,
    desserializar_compromisso,
    serializar_compromisso,
)

ID_1 = UUID(int=1)
ID_2 = UUID(int=2)


def compromisso(**alteracoes):
    dados = {
        "descricao": "Internet",
        "valor": Decimal("116.50"),
        "vencimento": date(2026, 12, 10),
        "tipo": TipoCompromisso.ASSINATURA,
        "status": StatusCompromisso.PENDENTE,
    }
    dados.update(alteracoes)
    return CompromissoFinanceiro(**dados)


def preparar_repositorio(linhas=None):
    linhas = [CABECALHO.copy()] if linhas is None else linhas
    aba = SimpleNamespace(
        get_all_values=Mock(return_value=linhas),
        append_row=Mock(),
        update=Mock(),
        cell=Mock(),
    )
    planilha = SimpleNamespace(worksheet=Mock(return_value=aba), sheet1=Mock())
    repositorio = RepositorioCompromissosSheets(planilha)
    planilha.worksheet.assert_called_once_with("Compromissos")
    planilha.sheet1.assert_not_called()
    return repositorio, aba, planilha


@pytest.mark.parametrize(
    ("valor", "formatado"),
    [
        ("0.01", "0,01"),
        ("116.50", "116,50"),
        ("1234.56", "1.234,56"),
        ("10000.00", "10.000,00"),
    ],
)
def test_serializacao_e_desserializacao_monetaria_brasileira(valor, formatado):
    original = compromisso(valor=Decimal(valor))

    linha = serializar_compromisso(ID_1, original)
    recuperado = desserializar_compromisso(linha)

    assert linha == [
        str(ID_1),
        "Internet",
        formatado,
        "10/12/2026",
        "assinatura",
        "pendente",
    ]
    assert recuperado.identificador == ID_1
    assert recuperado.compromisso == original
    assert recuperado.compromisso.valor.as_tuple().exponent == -2


@pytest.mark.parametrize("valor_texto", ["R$ 116,50", "R$116,50", "R$\u00a0116,50"])
def test_desserializacao_aceita_valor_com_simbolo_brasileiro(valor_texto):
    linha = serializar_compromisso(ID_1, compromisso())
    linha[2] = valor_texto

    assert desserializar_compromisso(linha).compromisso.valor == Decimal("116.50")


def test_salvar_cria_na_aba_compromissos_sem_tocar_movimentacoes(monkeypatch):
    repositorio, aba, planilha = preparar_repositorio()
    monkeypatch.setattr(modulo_sheets, "uuid4", lambda: ID_1)
    original = compromisso()

    salvo = repositorio.salvar(original)

    assert salvo.identificador == ID_1
    assert salvo.compromisso is original
    aba.append_row.assert_called_once_with(
        serializar_compromisso(ID_1, original), value_input_option="RAW"
    )
    aba.update.assert_not_called()
    planilha.sheet1.assert_not_called()


def test_aba_ausente_ou_falha_ao_selecionar_nao_cria_aba():
    planilha = SimpleNamespace(
        worksheet=Mock(side_effect=WorksheetNotFound("Compromissos")),
        add_worksheet=Mock(),
    )
    with pytest.raises(DadosCompromissosInvalidosError, match="não existe"):
        RepositorioCompromissosSheets(planilha)
    planilha.add_worksheet.assert_not_called()

    planilha.worksheet.side_effect = RuntimeError("falha externa")
    with pytest.raises(RepositorioSheetsLeituraError):
        RepositorioCompromissosSheets(planilha)
    planilha.add_worksheet.assert_not_called()


def test_salvar_gera_uuid_novo_em_colisao(monkeypatch):
    linha = serializar_compromisso(ID_1, compromisso())
    repositorio, aba, _ = preparar_repositorio([CABECALHO, linha])
    ids = iter([ID_1, ID_2])
    monkeypatch.setattr(modulo_sheets, "uuid4", lambda: next(ids))

    salvo = repositorio.salvar(compromisso(descricao="Aluguel"))

    assert salvo.identificador == ID_2
    assert aba.append_row.call_args.args[0][0] == str(ID_2)


def test_salvar_rejeita_objeto_invalido_antes_de_acessar_a_aba():
    repositorio, aba, _ = preparar_repositorio()

    with pytest.raises(EntradaInvalidaError, match="Compromisso financeiro"):
        repositorio.salvar({"descricao": "inválida"})

    aba.get_all_values.assert_not_called()
    aba.append_row.assert_not_called()


def test_buscar_recupera_uuid_data_valor_e_enums():
    original = compromisso(status=StatusCompromisso.PAGO)
    repositorio, _, _ = preparar_repositorio(
        [CABECALHO, serializar_compromisso(ID_1, original)]
    )

    recuperado = repositorio.buscar(ID_1)

    assert recuperado.identificador == ID_1
    assert recuperado.compromisso.valor == Decimal("116.50")
    assert recuperado.compromisso.vencimento == date(2026, 12, 10)
    assert recuperado.compromisso.tipo is TipoCompromisso.ASSINATURA
    assert recuperado.compromisso.status is StatusCompromisso.PAGO


def test_listar_preserva_ordem_e_nao_altera_linhas_existentes():
    linhas = [
        CABECALHO.copy(),
        serializar_compromisso(ID_1, compromisso()),
        serializar_compromisso(ID_2, compromisso(descricao="Aluguel")),
    ]
    copia = [linha.copy() for linha in linhas]
    repositorio, aba, _ = preparar_repositorio(linhas)

    resultado = repositorio.listar()

    assert [item.identificador for item in resultado] == [ID_1, ID_2]
    assert linhas == copia
    aba.append_row.assert_not_called()
    aba.update.assert_not_called()


def test_atualizar_preserva_id_e_confere_a_celula_antes_de_escrever():
    original = compromisso()
    alterado = original.atualizar(valor="10000.00").marcar_como_pago()
    repositorio, aba, _ = preparar_repositorio(
        [CABECALHO, serializar_compromisso(ID_1, original)]
    )
    aba.cell.return_value = SimpleNamespace(value=str(ID_1))

    resultado = repositorio.atualizar(ID_1, alterado)

    assert resultado.identificador == ID_1
    assert resultado.compromisso is alterado
    aba.cell.assert_called_once_with(2, 1)
    aba.update.assert_called_once_with(
        range_name="A2:F2",
        values=[serializar_compromisso(ID_1, alterado)],
        value_input_option="RAW",
    )
    aba.append_row.assert_not_called()


def test_atualizar_relocaliza_registro_quando_linha_muda():
    original = compromisso()
    outra = compromisso(descricao="Aluguel")
    primeira_leitura = [CABECALHO, serializar_compromisso(ID_1, original)]
    segunda_leitura = [
        CABECALHO,
        serializar_compromisso(ID_2, outra),
        serializar_compromisso(ID_1, original),
    ]
    repositorio, aba, _ = preparar_repositorio()
    aba.get_all_values.side_effect = [primeira_leitura, segunda_leitura]
    aba.cell.side_effect = [
        SimpleNamespace(value=str(ID_2)),
        SimpleNamespace(value=str(ID_1)),
    ]
    alterado = original.marcar_como_pago()

    repositorio.atualizar(ID_1, alterado)

    aba.update.assert_called_once_with(
        range_name="A3:F3",
        values=[serializar_compromisso(ID_1, alterado)],
        value_input_option="RAW",
    )
    assert segunda_leitura[1] == serializar_compromisso(ID_2, outra)


@pytest.mark.parametrize("linha_vazia", [[], ["", "", "", "", "", ""]])
def test_atualizar_preserva_numero_fisico_com_linha_vazia_intermediaria(linha_vazia):
    original = compromisso()
    alterado = original.marcar_como_pago()
    repositorio, aba, _ = preparar_repositorio(
        [CABECALHO, linha_vazia, serializar_compromisso(ID_1, original)]
    )
    aba.cell.return_value = SimpleNamespace(value=str(ID_1))

    repositorio.atualizar(ID_1, alterado)

    aba.cell.assert_called_once_with(3, 1)
    aba.update.assert_called_once_with(
        range_name="A3:F3",
        values=[serializar_compromisso(ID_1, alterado)],
        value_input_option="RAW",
    )


def test_atualizar_falha_se_posicao_continua_mudando():
    original = compromisso()
    repositorio, aba, _ = preparar_repositorio(
        [CABECALHO, serializar_compromisso(ID_1, original)]
    )
    aba.cell.return_value = SimpleNamespace(value=str(ID_2))

    with pytest.raises(DadosCompromissosInvalidosError, match="posição"):
        repositorio.atualizar(ID_1, original)

    aba.update.assert_not_called()


def test_atualizar_trata_falhas_de_api_na_conferencia_e_na_escrita():
    original = compromisso()
    repositorio, aba, _ = preparar_repositorio(
        [CABECALHO, serializar_compromisso(ID_1, original)]
    )
    aba.cell.side_effect = RuntimeError("falha de leitura")
    with pytest.raises(RepositorioSheetsLeituraError):
        repositorio.atualizar(ID_1, original)
    aba.update.assert_not_called()

    aba.cell.side_effect = None
    aba.cell.return_value = SimpleNamespace(value=str(ID_1))
    aba.update.side_effect = RuntimeError("falha de escrita")
    with pytest.raises(RepositorioSheetsEscritaError):
        repositorio.atualizar(ID_1, original)


def test_buscar_e_atualizar_id_inexistente_falham_sem_escrita():
    repositorio, aba, _ = preparar_repositorio()

    with pytest.raises(CompromissoNaoEncontradoError):
        repositorio.buscar(ID_1)
    with pytest.raises(CompromissoNaoEncontradoError):
        repositorio.atualizar(ID_1, compromisso())

    aba.update.assert_not_called()


@pytest.mark.parametrize("identificador", [None, "id", 123])
def test_buscar_e_atualizar_rejeitam_identificadores_invalidos(identificador):
    repositorio, aba, _ = preparar_repositorio()

    with pytest.raises(EntradaInvalidaError, match="Identificador"):
        repositorio.buscar(identificador)
    with pytest.raises(EntradaInvalidaError, match="Identificador"):
        repositorio.atualizar(identificador, compromisso())

    aba.get_all_values.assert_not_called()


def test_identificadores_duplicados_bloqueiam_leitura_e_escrita():
    original = compromisso()
    linha = serializar_compromisso(ID_1, original)
    repositorio, aba, _ = preparar_repositorio([CABECALHO, linha, linha.copy()])

    with pytest.raises(CompromissoDuplicadoError):
        repositorio.listar()
    with pytest.raises(CompromissoDuplicadoError):
        repositorio.atualizar(ID_1, original)

    aba.update.assert_not_called()


@pytest.mark.parametrize(
    "linha",
    [
        ["id", "Internet", "116,50", "10/12/2026", "assinatura", "pendente"],
        [str(ID_1), "Internet", "116,500", "10/12/2026", "assinatura", "pendente"],
        [str(ID_1), "Internet", "116,50", "31/02/2026", "assinatura", "pendente"],
        [str(ID_1), "Internet", "116,50", "10/12/2026", "cartão", "pendente"],
        [str(ID_1), "Internet", "116,50", "10/12/2026", "assinatura", "vencido"],
        [str(ID_1), "", "116,50", "10/12/2026", "assinatura", "pendente"],
        [str(ID_1), "Internet"],
    ],
)
def test_registro_invalido_recuperado_e_rejeitado(linha):
    repositorio, aba, _ = preparar_repositorio([CABECALHO, linha])

    with pytest.raises(DadosCompromissosInvalidosError):
        repositorio.listar()

    aba.update.assert_not_called()


def test_cabecalho_invalido_bloqueia_criacao():
    repositorio, aba, _ = preparar_repositorio([["ID", "Valor"]])

    with pytest.raises(DadosCompromissosInvalidosError, match="Cabeçalho"):
        repositorio.salvar(compromisso())

    aba.append_row.assert_not_called()


@pytest.mark.parametrize(
    "linhas",
    [None, {"valores": []}, [CABECALHO, None], [CABECALHO, "linha"]],
)
def test_estrutura_de_linhas_inconsistente_gera_erro_explicito(linhas):
    repositorio, aba, _ = preparar_repositorio(linhas)
    aba.get_all_values.return_value = linhas

    with pytest.raises(DadosCompromissosInvalidosError):
        repositorio.listar()

    aba.append_row.assert_not_called()
    aba.update.assert_not_called()


def test_falhas_de_api_na_leitura_e_escrita_sao_explicitas():
    repositorio, aba, _ = preparar_repositorio()
    aba.get_all_values.side_effect = RuntimeError("falha externa")
    with pytest.raises(RepositorioSheetsLeituraError):
        repositorio.listar()

    aba.get_all_values.side_effect = None
    aba.append_row.side_effect = RuntimeError("falha externa")
    with pytest.raises(RepositorioSheetsEscritaError):
        repositorio.salvar(compromisso())


def test_timeout_apos_criacao_bem_sucedida_nao_duplica(monkeypatch):
    linhas = [CABECALHO.copy()]
    repositorio, aba, _ = preparar_repositorio(linhas)
    monkeypatch.setattr(modulo_sheets, "uuid4", lambda: ID_1)
    original = compromisso()

    def criar_e_falhar(linha, **_kwargs):
        linhas.append(linha)
        raise Timeout("resposta perdida")

    aba.append_row.side_effect = criar_e_falhar

    salvo = repositorio.salvar(original)

    assert salvo.identificador == ID_1
    assert salvo.compromisso == original
    aba.append_row.assert_called_once()
    assert len(linhas) == 2


def test_timeout_sem_confirmacao_nao_repete_criacao(monkeypatch):
    repositorio, aba, _ = preparar_repositorio()
    monkeypatch.setattr(modulo_sheets, "uuid4", lambda: ID_1)
    aba.append_row.side_effect = Timeout("resposta perdida")

    with pytest.raises(CriacaoIndeterminadaError) as capturado:
        repositorio.salvar(compromisso())

    assert capturado.value.identificador == ID_1
    assert capturado.value.__cause__ is aba.append_row.side_effect
    aba.append_row.assert_called_once()


def test_timeout_na_escrita_e_falha_na_leitura_preserva_uuid_e_causas(monkeypatch):
    repositorio, aba, _ = preparar_repositorio()
    monkeypatch.setattr(modulo_sheets, "uuid4", lambda: ID_1)
    erro_escrita = Timeout("resposta perdida")
    erro_leitura = RuntimeError("falha na confirmação")
    aba.append_row.side_effect = erro_escrita
    aba.get_all_values.side_effect = [[CABECALHO.copy()], erro_leitura]

    with pytest.raises(CriacaoIndeterminadaError) as capturado:
        repositorio.salvar(compromisso())

    assert capturado.value.identificador == ID_1
    assert capturado.value.erro_escrita is erro_escrita
    assert isinstance(capturado.value.__cause__, RepositorioSheetsLeituraError)
    assert capturado.value.__cause__.__cause__ is erro_leitura
    assert "resposta perdida" not in str(capturado.value)
    assert "falha na confirmação" not in str(capturado.value)
    aba.append_row.assert_called_once()
    assert aba.get_all_values.call_count == 2


def test_timeout_com_uuid_duplicado_falha_sem_repetir(monkeypatch):
    original = compromisso()
    linhas = [CABECALHO.copy()]
    repositorio, aba, _ = preparar_repositorio(linhas)
    monkeypatch.setattr(modulo_sheets, "uuid4", lambda: ID_1)

    def duplicar_e_falhar(linha, **_kwargs):
        linhas.extend([linha, linha.copy()])
        raise Timeout("resposta perdida")

    aba.append_row.side_effect = duplicar_e_falhar

    with pytest.raises(CompromissoDuplicadoError):
        repositorio.salvar(original)

    aba.append_row.assert_called_once()


def test_timeout_com_uuid_recuperado_mas_dados_divergentes_falha(monkeypatch):
    linhas = [CABECALHO.copy()]
    repositorio, aba, _ = preparar_repositorio(linhas)
    monkeypatch.setattr(modulo_sheets, "uuid4", lambda: ID_1)

    def criar_diferente_e_falhar(_linha, **_kwargs):
        linhas.append(serializar_compromisso(ID_1, compromisso(descricao="Outro")))
        raise Timeout("resposta perdida")

    aba.append_row.side_effect = criar_diferente_e_falhar

    with pytest.raises(DadosCompromissosInvalidosError, match="diverge"):
        repositorio.salvar(compromisso())

    aba.append_row.assert_called_once()
