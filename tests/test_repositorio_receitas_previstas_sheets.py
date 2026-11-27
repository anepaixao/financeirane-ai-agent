from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import UUID

import pytest
from gspread.exceptions import WorksheetNotFound
from requests.exceptions import Timeout

import financeirane.repositories.receitas_previstas_sheets as modulo_sheets
from financeirane.domain.exceptions import EntradaInvalidaError
from financeirane.domain.receitas_previstas import ReceitaPrevista, StatusReceita
from financeirane.repositories.receitas_previstas import (
    ReceitaPrevistaNaoEncontradaError,
    RepositorioReceitasPrevistas,
)
from financeirane.repositories.receitas_previstas_sheets import (
    CABECALHO,
    CriacaoReceitaIndeterminadaError,
    DadosReceitasPrevistasInvalidosError,
    ReceitaPrevistaDuplicadaError,
    RepositorioReceitasPrevistasSheets,
    RepositorioReceitasSheetsEscritaError,
    RepositorioReceitasSheetsLeituraError,
    desserializar_receita,
    serializar_receita,
)

ID_1 = UUID(int=1)
ID_2 = UUID(int=2)


def receita(**alteracoes):
    dados = {
        "descricao": "Salário",
        "valor": Decimal("116.50"),
        "data_prevista": date(2026, 12, 7),
        "status": StatusReceita.PREVISTA,
    }
    dados.update(alteracoes)
    return ReceitaPrevista(**dados)


def preparar_repositorio(linhas=None):
    linhas = [CABECALHO.copy()] if linhas is None else linhas
    aba = SimpleNamespace(
        get_all_values=Mock(return_value=linhas),
        append_row=Mock(),
        update=Mock(),
        cell=Mock(),
    )
    planilha = SimpleNamespace(
        worksheet=Mock(return_value=aba), sheet1=Mock(), add_worksheet=Mock()
    )
    repositorio: RepositorioReceitasPrevistas = RepositorioReceitasPrevistasSheets(
        planilha
    )
    planilha.worksheet.assert_called_once_with("Receitas Previstas")
    planilha.sheet1.assert_not_called()
    planilha.add_worksheet.assert_not_called()
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
    original = receita(valor=Decimal(valor))

    linha = serializar_receita(ID_1, original)
    recuperada = desserializar_receita(linha)

    assert linha == [str(ID_1), "Salário", formatado, "07/12/2026", "prevista"]
    assert recuperada.identificador == ID_1
    assert recuperada.receita == original
    assert recuperada.receita.valor.as_tuple().exponent == -2
    assert recuperada.receita.status is StatusReceita.PREVISTA


@pytest.mark.parametrize("valor_texto", ["R$ 116,50", "R$116,50", "R$\u00a0116,50"])
def test_desserializacao_aceita_valor_com_simbolo_brasileiro(valor_texto):
    linha = serializar_receita(ID_1, receita())
    linha[2] = valor_texto

    assert desserializar_receita(linha).receita.valor == Decimal("116.50")


def test_salvar_cria_na_aba_especifica_sem_tocar_outras_abas(monkeypatch):
    repositorio, aba, planilha = preparar_repositorio()
    monkeypatch.setattr(modulo_sheets, "uuid4", lambda: ID_1)
    original = receita()

    salva = repositorio.salvar(original)

    assert salva.identificador == ID_1
    assert salva.receita is original
    aba.append_row.assert_called_once_with(
        serializar_receita(ID_1, original), value_input_option="RAW"
    )
    aba.update.assert_not_called()
    planilha.worksheet.assert_called_once_with("Receitas Previstas")
    planilha.sheet1.assert_not_called()


def test_aba_ausente_ou_falha_ao_selecionar_nao_cria_aba():
    planilha = SimpleNamespace(
        worksheet=Mock(side_effect=WorksheetNotFound("Receitas Previstas")),
        add_worksheet=Mock(),
    )
    with pytest.raises(DadosReceitasPrevistasInvalidosError, match="não existe"):
        RepositorioReceitasPrevistasSheets(planilha)
    planilha.add_worksheet.assert_not_called()

    planilha.worksheet.side_effect = RuntimeError("falha externa")
    with pytest.raises(RepositorioReceitasSheetsLeituraError):
        RepositorioReceitasPrevistasSheets(planilha)
    planilha.add_worksheet.assert_not_called()


def test_salvar_gera_uuid_novo_em_colisao(monkeypatch):
    linha = serializar_receita(ID_1, receita())
    repositorio, aba, _ = preparar_repositorio([CABECALHO, linha])
    ids = iter([ID_1, ID_2])
    monkeypatch.setattr(modulo_sheets, "uuid4", lambda: next(ids))

    salva = repositorio.salvar(receita(descricao="Freelance"))

    assert salva.identificador == ID_2
    assert aba.append_row.call_args.args[0][0] == str(ID_2)


def test_salvar_rejeita_objeto_invalido_antes_de_ler_aba():
    repositorio, aba, _ = preparar_repositorio()

    with pytest.raises(EntradaInvalidaError, match="Receita prevista inválida"):
        repositorio.salvar({"descricao": "inválida"})

    aba.get_all_values.assert_not_called()
    aba.append_row.assert_not_called()


def test_buscar_recupera_uuid_valor_data_e_status():
    original = receita()
    repositorio, _, _ = preparar_repositorio(
        [CABECALHO, serializar_receita(ID_1, original)]
    )

    recuperada = repositorio.buscar(ID_1)

    assert recuperada.identificador == ID_1
    assert recuperada.receita.valor == Decimal("116.50")
    assert recuperada.receita.data_prevista == date(2026, 12, 7)
    assert recuperada.receita.status is StatusReceita.PREVISTA


def test_listar_preserva_ordem_e_nao_altera_linhas_existentes():
    linhas = [
        CABECALHO.copy(),
        serializar_receita(ID_1, receita()),
        serializar_receita(ID_2, receita(descricao="Freelance")),
    ]
    copia = [linha.copy() for linha in linhas]
    repositorio, aba, _ = preparar_repositorio(linhas)

    resultado = repositorio.listar()

    assert [item.identificador for item in resultado] == [ID_1, ID_2]
    assert linhas == copia
    aba.append_row.assert_not_called()
    aba.update.assert_not_called()


def test_atualizar_preserva_id_e_confere_celula_antes_de_escrever():
    original = receita()
    alterada = receita(valor="10000.00")
    repositorio, aba, _ = preparar_repositorio(
        [CABECALHO, serializar_receita(ID_1, original)]
    )
    aba.cell.return_value = SimpleNamespace(value=str(ID_1))

    resultado = repositorio.atualizar(ID_1, alterada)

    assert resultado.identificador == ID_1
    assert resultado.receita is alterada
    aba.cell.assert_called_once_with(2, 1)
    aba.update.assert_called_once_with(
        range_name="A2:E2",
        values=[serializar_receita(ID_1, alterada)],
        value_input_option="RAW",
    )
    aba.append_row.assert_not_called()


def test_atualizar_relocaliza_registro_quando_linha_muda():
    original = receita()
    outra = receita(descricao="Freelance")
    primeira_leitura = [CABECALHO, serializar_receita(ID_1, original)]
    segunda_leitura = [
        CABECALHO,
        serializar_receita(ID_2, outra),
        serializar_receita(ID_1, original),
    ]
    repositorio, aba, _ = preparar_repositorio()
    aba.get_all_values.side_effect = [primeira_leitura, segunda_leitura]
    aba.cell.side_effect = [
        SimpleNamespace(value=str(ID_2)),
        SimpleNamespace(value=str(ID_1)),
    ]
    alterada = receita(valor="150.00")

    repositorio.atualizar(ID_1, alterada)

    aba.update.assert_called_once_with(
        range_name="A3:E3",
        values=[serializar_receita(ID_1, alterada)],
        value_input_option="RAW",
    )
    assert segunda_leitura[1] == serializar_receita(ID_2, outra)


@pytest.mark.parametrize("linha_vazia", [[], ["", "", "", "", ""]])
def test_atualizar_preserva_numero_fisico_com_linha_vazia_intermediaria(linha_vazia):
    original = receita()
    alterada = receita(valor="150.00")
    repositorio, aba, _ = preparar_repositorio(
        [CABECALHO, linha_vazia, serializar_receita(ID_1, original)]
    )
    aba.cell.return_value = SimpleNamespace(value=str(ID_1))

    repositorio.atualizar(ID_1, alterada)

    aba.cell.assert_called_once_with(3, 1)
    aba.update.assert_called_once_with(
        range_name="A3:E3",
        values=[serializar_receita(ID_1, alterada)],
        value_input_option="RAW",
    )


def test_atualizar_falha_se_posicao_continua_mudando():
    original = receita()
    repositorio, aba, _ = preparar_repositorio(
        [CABECALHO, serializar_receita(ID_1, original)]
    )
    aba.cell.return_value = SimpleNamespace(value=str(ID_2))

    with pytest.raises(DadosReceitasPrevistasInvalidosError, match="posição"):
        repositorio.atualizar(ID_1, original)

    aba.update.assert_not_called()


def test_atualizar_trata_falhas_de_api_na_conferencia_e_na_escrita():
    original = receita()
    repositorio, aba, _ = preparar_repositorio(
        [CABECALHO, serializar_receita(ID_1, original)]
    )
    aba.cell.side_effect = RuntimeError("falha de leitura")
    with pytest.raises(RepositorioReceitasSheetsLeituraError):
        repositorio.atualizar(ID_1, original)
    aba.update.assert_not_called()

    aba.cell.side_effect = None
    aba.cell.return_value = SimpleNamespace(value=str(ID_1))
    aba.update.side_effect = RuntimeError("falha de escrita")
    with pytest.raises(RepositorioReceitasSheetsEscritaError):
        repositorio.atualizar(ID_1, original)


def test_buscar_e_atualizar_id_inexistente_falham_sem_escrita():
    repositorio, aba, _ = preparar_repositorio()

    with pytest.raises(ReceitaPrevistaNaoEncontradaError):
        repositorio.buscar(ID_1)
    with pytest.raises(ReceitaPrevistaNaoEncontradaError):
        repositorio.atualizar(ID_1, receita())

    aba.update.assert_not_called()


@pytest.mark.parametrize("identificador", [None, "id", 123, []])
def test_buscar_e_atualizar_rejeitam_identificadores_invalidos(identificador):
    repositorio, aba, _ = preparar_repositorio()

    with pytest.raises(EntradaInvalidaError, match="Identificador"):
        repositorio.buscar(identificador)
    with pytest.raises(EntradaInvalidaError, match="Identificador"):
        repositorio.atualizar(identificador, receita())

    aba.get_all_values.assert_not_called()


def test_atualizar_rejeita_objeto_invalido_antes_de_ler_aba():
    repositorio, aba, _ = preparar_repositorio()

    with pytest.raises(EntradaInvalidaError, match="Receita prevista inválida"):
        repositorio.atualizar(ID_1, {})

    aba.get_all_values.assert_not_called()


def test_identificadores_duplicados_bloqueiam_leitura_e_escrita():
    original = receita()
    linha = serializar_receita(ID_1, original)
    repositorio, aba, _ = preparar_repositorio([CABECALHO, linha, linha.copy()])

    with pytest.raises(ReceitaPrevistaDuplicadaError):
        repositorio.listar()
    with pytest.raises(ReceitaPrevistaDuplicadaError):
        repositorio.atualizar(ID_1, original)
    with pytest.raises(ReceitaPrevistaDuplicadaError):
        repositorio.salvar(original)

    aba.append_row.assert_not_called()
    aba.update.assert_not_called()


@pytest.mark.parametrize(
    "linha",
    [
        ["id", "Salário", "116,50", "07/12/2026", "prevista"],
        [str(ID_1), "Salário", "116,500", "07/12/2026", "prevista"],
        [str(ID_1), "Salário", "116,50", "31/02/2026", "prevista"],
        [str(ID_1), "Salário", "116,50", "07/12/2026", "recebida"],
        [str(ID_1), "", "116,50", "07/12/2026", "prevista"],
        [str(ID_1), "Salário", "-116,50", "07/12/2026", "prevista"],
        [str(ID_1), "Salário", "0,00", "07/12/2026", "prevista"],
        [str(ID_1), "Salário"],
    ],
)
def test_registro_invalido_recuperado_e_rejeitado(linha):
    repositorio, aba, _ = preparar_repositorio([CABECALHO, linha])

    with pytest.raises(DadosReceitasPrevistasInvalidosError):
        repositorio.listar()

    aba.update.assert_not_called()


def test_cabecalho_invalido_bloqueia_criacao():
    repositorio, aba, _ = preparar_repositorio([["ID", "Valor"]])

    with pytest.raises(DadosReceitasPrevistasInvalidosError, match="Cabeçalho"):
        repositorio.salvar(receita())

    aba.append_row.assert_not_called()


@pytest.mark.parametrize(
    "linhas", [None, {"valores": []}, [CABECALHO, None], [CABECALHO, "linha"]]
)
def test_estrutura_de_linhas_inconsistente_gera_erro_explicito(linhas):
    repositorio, aba, _ = preparar_repositorio(linhas)
    aba.get_all_values.return_value = linhas

    with pytest.raises(DadosReceitasPrevistasInvalidosError):
        repositorio.listar()

    aba.append_row.assert_not_called()
    aba.update.assert_not_called()


def test_falhas_de_api_na_leitura_e_escrita_sao_explicitas():
    repositorio, aba, _ = preparar_repositorio()
    aba.get_all_values.side_effect = RuntimeError("falha externa")
    with pytest.raises(RepositorioReceitasSheetsLeituraError):
        repositorio.listar()

    aba.get_all_values.side_effect = None
    aba.append_row.side_effect = RuntimeError("falha externa")
    with pytest.raises(RepositorioReceitasSheetsEscritaError):
        repositorio.salvar(receita())


def test_timeout_apos_criacao_confirmada_nao_duplica(monkeypatch):
    linhas = [CABECALHO.copy()]
    repositorio, aba, _ = preparar_repositorio(linhas)
    monkeypatch.setattr(modulo_sheets, "uuid4", lambda: ID_1)
    original = receita()

    def criar_e_falhar(linha, **_kwargs):
        linhas.append(linha)
        raise Timeout("resposta perdida")

    aba.append_row.side_effect = criar_e_falhar

    salva = repositorio.salvar(original)

    assert salva.identificador == ID_1
    assert salva.receita == original
    aba.append_row.assert_called_once()
    assert len(linhas) == 2


def test_timeout_sem_confirmacao_nao_repete_criacao(monkeypatch):
    repositorio, aba, _ = preparar_repositorio()
    monkeypatch.setattr(modulo_sheets, "uuid4", lambda: ID_1)
    aba.append_row.side_effect = Timeout("resposta perdida")

    with pytest.raises(CriacaoReceitaIndeterminadaError) as capturado:
        repositorio.salvar(receita())

    assert capturado.value.identificador == ID_1
    assert capturado.value.__cause__ is aba.append_row.side_effect
    aba.append_row.assert_called_once()


def test_timeout_e_falha_na_leitura_preserva_uuid_e_causas(monkeypatch):
    repositorio, aba, _ = preparar_repositorio()
    monkeypatch.setattr(modulo_sheets, "uuid4", lambda: ID_1)
    erro_escrita = Timeout("resposta perdida")
    erro_leitura = RuntimeError("falha na confirmação")
    aba.append_row.side_effect = erro_escrita
    aba.get_all_values.side_effect = [[CABECALHO.copy()], erro_leitura]

    with pytest.raises(CriacaoReceitaIndeterminadaError) as capturado:
        repositorio.salvar(receita())

    assert capturado.value.identificador == ID_1
    assert capturado.value.erro_escrita is erro_escrita
    assert isinstance(capturado.value.__cause__, RepositorioReceitasSheetsLeituraError)
    assert capturado.value.__cause__.__cause__ is erro_leitura
    assert "resposta perdida" not in str(capturado.value)
    assert "falha na confirmação" not in str(capturado.value)
    aba.append_row.assert_called_once()
    assert aba.get_all_values.call_count == 2


def test_timeout_e_leitura_invalida_preserva_uuid_sem_repetir(monkeypatch):
    repositorio, aba, _ = preparar_repositorio()
    monkeypatch.setattr(modulo_sheets, "uuid4", lambda: ID_1)
    aba.append_row.side_effect = Timeout("resposta perdida")
    aba.get_all_values.side_effect = [[CABECALHO.copy()], [["ID", "Valor"]]]

    with pytest.raises(CriacaoReceitaIndeterminadaError) as capturado:
        repositorio.salvar(receita())

    assert capturado.value.identificador == ID_1
    assert isinstance(capturado.value.__cause__, DadosReceitasPrevistasInvalidosError)
    aba.append_row.assert_called_once()


def test_timeout_com_uuid_duplicado_falha_sem_repetir(monkeypatch):
    original = receita()
    linhas = [CABECALHO.copy()]
    repositorio, aba, _ = preparar_repositorio(linhas)
    monkeypatch.setattr(modulo_sheets, "uuid4", lambda: ID_1)

    def duplicar_e_falhar(linha, **_kwargs):
        linhas.extend([linha, linha.copy()])
        raise Timeout("resposta perdida")

    aba.append_row.side_effect = duplicar_e_falhar

    with pytest.raises(ReceitaPrevistaDuplicadaError):
        repositorio.salvar(original)

    aba.append_row.assert_called_once()


def test_timeout_com_uuid_recuperado_e_dados_divergentes_falha(monkeypatch):
    linhas = [CABECALHO.copy()]
    repositorio, aba, _ = preparar_repositorio(linhas)
    monkeypatch.setattr(modulo_sheets, "uuid4", lambda: ID_1)

    def criar_diferente_e_falhar(_linha, **_kwargs):
        linhas.append(serializar_receita(ID_1, receita(descricao="Outro")))
        raise Timeout("resposta perdida")

    aba.append_row.side_effect = criar_diferente_e_falhar

    with pytest.raises(DadosReceitasPrevistasInvalidosError, match="diverge"):
        repositorio.salvar(receita())

    aba.append_row.assert_called_once()
