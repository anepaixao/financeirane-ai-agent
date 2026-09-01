import os
from types import SimpleNamespace
from unittest.mock import Mock, call

import pytest
from gspread.exceptions import APIError

os.environ.setdefault("TELEGRAM_TOKEN", "telegram-token-ficticio")
os.environ.setdefault("GEMINI_API_KEY", "gemini-api-key-ficticia")
os.environ.setdefault("AUTHORIZED_CHAT_IDS", "123456789")

import sheets_service
from config import GOOGLE_CREDENTIALS_FILE, MAX_PARCELAS, SPREADSHEET_NAME
from models import RegistroFinanceiro
from sheets_service import (
    PlanilhaEscritaError,
    conectar_planilha,
    consultar_gastos_mes,
    erro_transiente_google,
    inserir_linhas_com_retry,
    obter_status_code_google,
    registrar_movimentacao,
)


class TimeoutFakeError(Exception):
    pass


class ConnectionFakeError(Exception):
    pass


def criar_api_error(status_code):
    resposta = SimpleNamespace(status_code=status_code, text="erro ficticio")
    resposta.json = Mock(
        return_value={
            "error": {
                "code": status_code,
                "message": "erro ficticio",
                "status": "STATUS_FICTICIO",
            }
        }
    )
    return APIError(resposta)


def criar_registro(**overrides):
    dados = {
        "data": "31/01/2026",
        "tipo": "gasto",
        "valor_total": 100.0,
        "descricao": "Mercado",
        "parcelas": 1,
        "categoria": "Outros",
    }
    dados.update(overrides)
    return RegistroFinanceiro(**dados)


def test_conectar_planilha_usa_credenciais_e_nome_configurados(monkeypatch):
    planilha = object()
    arquivo = SimpleNamespace(sheet1=planilha)
    cliente = SimpleNamespace(open=Mock(return_value=arquivo))
    service_account = Mock(return_value=cliente)
    monkeypatch.setattr(sheets_service.gspread, "service_account", service_account)

    resultado = conectar_planilha()

    assert resultado is planilha
    service_account.assert_called_once_with(filename=GOOGLE_CREDENTIALS_FILE)
    cliente.open.assert_called_once_with(SPREADSHEET_NAME)


def test_obter_status_code_google_retorna_status_quando_existe():
    erro = criar_api_error(503)

    assert obter_status_code_google(erro) == 503


def test_obter_status_code_google_retorna_none_sem_response_ou_status():
    assert obter_status_code_google(Exception("erro")) is None
    assert obter_status_code_google(SimpleNamespace(response=object())) is None


@pytest.mark.parametrize("status_code", [408, 429, 500, 502, 503, 504])
def test_erro_transiente_google_reconhece_api_error_transitorio(status_code):
    assert erro_transiente_google(criar_api_error(status_code)) is True


@pytest.mark.parametrize("status_code", [400, 401, 403, 404])
def test_erro_transiente_google_rejeita_api_error_nao_transitorio(status_code):
    assert erro_transiente_google(criar_api_error(status_code)) is False


@pytest.mark.parametrize("erro", [TimeoutFakeError(), ConnectionFakeError()])
def test_erro_transiente_google_reconhece_timeout_e_connection_error(erro):
    assert erro_transiente_google(erro) is True


def test_erro_transiente_google_rejeita_erro_comum():
    assert erro_transiente_google(ValueError("erro")) is False


def test_inserir_linhas_com_retry_sucesso_na_primeira_tentativa(monkeypatch):
    sleep = Mock()
    planilha = SimpleNamespace(insert_rows=Mock())
    linhas = [["01/08/2026", "gasto"]]
    monkeypatch.setattr(sheets_service.time, "sleep", sleep)

    inserir_linhas_com_retry(planilha, linhas, index=2)

    planilha.insert_rows.assert_called_once_with(linhas, row=2)
    sleep.assert_not_called()


def test_inserir_linhas_com_retry_erro_transitorio_seguido_de_sucesso(monkeypatch):
    sleep = Mock()
    erro = TimeoutFakeError("timeout")
    planilha = SimpleNamespace(insert_rows=Mock(side_effect=[erro, None]))
    linhas = [["01/08/2026", "gasto"]]
    monkeypatch.setattr(sheets_service.time, "sleep", sleep)

    inserir_linhas_com_retry(planilha, linhas, index=2)

    assert planilha.insert_rows.call_count == 2
    sleep.assert_called_once_with(sheets_service.TEMPO_ESPERA_INICIAL)


def test_inserir_linhas_com_retry_erro_nao_transitorio_gera_erro_customizado(
    monkeypatch,
):
    sleep = Mock()
    erro = ValueError("erro permanente")
    planilha = SimpleNamespace(insert_rows=Mock(side_effect=erro))
    linhas = [["01/08/2026", "gasto"]]
    monkeypatch.setattr(sheets_service.time, "sleep", sleep)

    with pytest.raises(PlanilhaEscritaError) as capturado:
        inserir_linhas_com_retry(planilha, linhas, index=2)

    assert capturado.value.__cause__ is erro
    planilha.insert_rows.assert_called_once_with(linhas, row=2)
    sleep.assert_not_called()


def test_inserir_linhas_com_retry_esgota_tentativas_com_backoff(monkeypatch):
    sleep = Mock()
    erro = criar_api_error(503)
    planilha = SimpleNamespace(insert_rows=Mock(side_effect=erro))
    linhas = [["01/08/2026", "gasto"], ["01/09/2026", "gasto"]]
    monkeypatch.setattr(sheets_service.time, "sleep", sleep)

    with pytest.raises(PlanilhaEscritaError) as capturado:
        inserir_linhas_com_retry(planilha, linhas, index=2)

    assert capturado.value.__cause__ is erro
    assert planilha.insert_rows.call_count == sheets_service.MAX_TENTATIVAS_ESCRITA
    assert sleep.call_args_list == [
        call(sheets_service.TEMPO_ESPERA_INICIAL),
        call(sheets_service.TEMPO_ESPERA_INICIAL * 2),
    ]


def test_inserir_linhas_com_retry_loga_quantidade_de_linhas_sem_conteudo(caplog):
    planilha = SimpleNamespace(insert_rows=Mock())
    linhas = [["01/08/2026", "gasto", "987654321", "mercado secreto"]]

    with caplog.at_level("INFO", logger="sheets_service"):
        inserir_linhas_com_retry(planilha, linhas, index=2)

    assert "total_linhas=1" in caplog.text
    assert "987654321" not in caplog.text
    assert "mercado secreto" not in caplog.text
    assert str(linhas) not in caplog.text


def test_registrar_movimentacao_gasto_simples_chama_retry_com_lote(monkeypatch):
    inserir = Mock()
    monkeypatch.setattr(sheets_service, "inserir_linhas_com_retry", inserir)
    planilha = object()

    resposta = registrar_movimentacao(planilha, criar_registro())

    inserir.assert_called_once_with(
        planilha,
        [["31/01/2026", "gasto", "100,00", "Mercado", 1, "Outros"]],
        2,
    )
    assert resposta == "✅ Registado!\nAdicionado: Mercado (Outros) - R$ 100.00."


def test_registrar_movimentacao_receita_simples_preserva_tipo_categoria(monkeypatch):
    inserir = Mock()
    monkeypatch.setattr(sheets_service, "inserir_linhas_com_retry", inserir)
    registro = criar_registro(
        tipo="receita",
        valor_total="2500.50",
        descricao="Freela",
        categoria="Outros",
    )

    resposta = registrar_movimentacao(object(), registro)

    linha = inserir.call_args.args[1][0]
    assert linha == ["31/01/2026", "receita", "2500,50", "Freela", 1, "Outros"]
    assert resposta == "✅ Registado!\nAdicionado: Freela (Outros) - R$ 2500.50."


def test_registrar_movimentacao_compra_parcelada_distribui_centavos_e_datas(
    monkeypatch,
):
    inserir = Mock()
    monkeypatch.setattr(sheets_service, "inserir_linhas_com_retry", inserir)
    registro = criar_registro(valor_total=100, parcelas=3, categoria="Feira")

    resposta = registrar_movimentacao(object(), registro)

    linhas = inserir.call_args.args[1]
    assert linhas == [
        ["31/01/2026", "gasto", "33,34", "Mercado (Parcela 1/3)", 3, "Feira"],
        ["28/02/2026", "gasto", "33,33", "Mercado (Parcela 2/3)", 3, "Feira"],
        ["31/03/2026", "gasto", "33,33", "Mercado (Parcela 3/3)", 3, "Feira"],
    ]
    assert sum(int(linha[2].replace(",", "")) for linha in linhas) == 10000
    inserir.assert_called_once()
    assert (
        resposta
        == "✅ Registado!\nCompra de R$ 100.00 (Feira) dividida em 3x lançada na planilha."
    )


def test_registrar_movimentacao_aplica_texto_seguro_na_descricao(monkeypatch):
    inserir = Mock()
    monkeypatch.setattr(sheets_service, "inserir_linhas_com_retry", inserir)
    registro = criar_registro(descricao=" =SOMA(A1:A2)\n")

    registrar_movimentacao(object(), registro)

    assert inserir.call_args.args[1][0][3] == "'=SOMA(A1:A2)"


@pytest.mark.parametrize(
    ("campo", "valor", "mensagem"),
    [
        ("valor_total", 0, "valor_total deve ser maior que zero"),
        ("parcelas", 0, "parcelas deve estar entre"),
        ("parcelas", MAX_PARCELAS + 1, "parcelas deve estar entre"),
    ],
)
def test_registrar_movimentacao_rejeita_valores_invalidos(
    monkeypatch, campo, valor, mensagem
):
    inserir = Mock()
    monkeypatch.setattr(sheets_service, "inserir_linhas_com_retry", inserir)
    registro = criar_registro(**{campo: valor})

    with pytest.raises(ValueError, match=mensagem):
        registrar_movimentacao(object(), registro)

    inserir.assert_not_called()


def test_registrar_movimentacao_logs_nao_expoem_dados_financeiros(
    monkeypatch,
    caplog,
):
    inserir = Mock()
    monkeypatch.setattr(sheets_service, "inserir_linhas_com_retry", inserir)
    registro = criar_registro(valor_total=987654321, descricao="mercado secreto")

    with caplog.at_level("INFO", logger="sheets_service"):
        registrar_movimentacao(object(), registro)

    assert "mercado secreto" not in caplog.text
    assert "987654321" not in caplog.text
    assert "Outros" not in caplog.text


def test_consultar_gastos_mes_retorna_resumo_com_soma_e_fallback_categoria():
    linhas = [
        ["Data", "Tipo", "Valor", "Descrição", "Parcelas", "Categoria"],
        ["05/08/2026", "gasto", "10,50", "Mercado", "1", "Feira"],
        ["15/08/2026", "gasto", "20,00", "Internet", "1"],
        ["20/08/2026", "receita", "999,99", "Salario", "1", "Outros"],
        ["05/09/2026", "gasto", "50,00", "Outro mes", "1", "Outros"],
    ]
    planilha = SimpleNamespace(get_all_values=Mock(return_value=linhas))

    resposta = consultar_gastos_mes(planilha, "08", "2026")

    assert "📊 *Resumo de Contas (08/2026)*" in resposta
    assert "• [Feira] Mercado: R$ 10.50" in resposta
    assert "• [Outros] Internet: R$ 20.00" in resposta
    assert "Salario" not in resposta
    assert "Outro mes" not in resposta
    assert "💰 *Total a pagar neste mês: R$ 30.50*" in resposta
    planilha.get_all_values.assert_called_once()


def test_consultar_gastos_mes_sem_gastos_retorna_mensagem_de_vazio():
    planilha = SimpleNamespace(
        get_all_values=Mock(
            return_value=[
                ["Data", "Tipo", "Valor", "Descrição", "Parcelas", "Categoria"],
                ["05/08/2026", "receita", "100,00", "Freela", "1", "Outros"],
            ]
        )
    )

    resposta = consultar_gastos_mes(planilha, "08", "2026")

    assert resposta == "🔍 Não encontrei nenhum gasto registado para o mês 08/2026."


def test_consultar_gastos_mes_ignora_linhas_invalidas_sem_interromper():
    linhas = [
        ["Data", "Tipo", "Valor", "Descrição", "Parcelas", "Categoria"],
        ["invalida", "gasto", "10,00", "Data invalida", "1", "Outros"],
        ["05/08/2026", "gasto", "valor", "Valor invalido", "1", "Outros"],
        ["05/08/2026", "gasto"],
        ["06/08/2026", "gasto", "5,00", "Valido", "1", "Outros"],
    ]
    planilha = SimpleNamespace(get_all_values=Mock(return_value=linhas))

    resposta = consultar_gastos_mes(planilha, "08", "2026")

    assert "Valido: R$ 5.00" in resposta
    assert "Data invalida" not in resposta
    assert "Valor invalido" not in resposta


def test_consultar_gastos_mes_nao_altera_conteudo_da_planilha():
    linhas = [
        ["Data", "Tipo", "Valor", "Descrição", "Parcelas", "Categoria"],
        ["05/08/2026", "gasto", "10,00", "Mercado", "1", "Feira"],
    ]
    copia_original = [linha.copy() for linha in linhas]
    planilha = SimpleNamespace(get_all_values=Mock(return_value=linhas))

    consultar_gastos_mes(planilha, "08", "2026")

    assert linhas == copia_original


def test_consultar_gastos_mes_logs_nao_expoem_conteudo_da_planilha(caplog):
    linhas = [
        ["Data", "Tipo", "Valor", "Descrição", "Parcelas", "Categoria"],
        ["05/08/2026", "gasto", "987654321,00", "mercado secreto", "1", "Feira"],
    ]
    planilha = SimpleNamespace(get_all_values=Mock(return_value=linhas))

    with caplog.at_level("INFO", logger="sheets_service"):
        consultar_gastos_mes(planilha, "08", "2026")

    assert "mercado secreto" not in caplog.text
    assert "987654321" not in caplog.text
    assert str(linhas) not in caplog.text
    assert sheets_service.GOOGLE_CREDENTIALS_FILE not in caplog.text
