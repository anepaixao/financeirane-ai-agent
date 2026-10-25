import importlib
import json
import os
import sys
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

os.environ.setdefault("TELEGRAM_TOKEN", "telegram-token-ficticio")
os.environ.setdefault("GEMINI_API_KEY", "gemini-api-key-ficticia")
os.environ.setdefault("AUTHORIZED_CHAT_IDS", "123456789")

import financeirane.ai_service as ai_service
from financeirane.domain.exceptions import EntradaInvalidaError, InterpretacaoIAError
from financeirane.domain.models import RegistroFinanceiro


class DataFixa:
    year = 2026

    @staticmethod
    def today():
        return DataFixa()

    def strftime(self, formato):
        assert formato == "%d/%m/%Y"
        return "21/08/2026"


@pytest.fixture(autouse=True)
def recarregar_ai_service(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "gemini-api-key-ficticia")
    sys.modules.pop("ai_service", None)
    sys.modules.pop("financeirane.ai_service", None)
    modulo = importlib.import_module("financeirane.ai_service")
    globals()["ai_service"] = modulo
    yield modulo


def json_registro_valido(**overrides):
    dados = {
        "intencao": "registrar",
        "data": "21/08/2026",
        "tipo": "gasto",
        "valor_total": 100.0,
        "descricao": "Mercado",
        "parcelas": 1,
        "categoria": "Outros",
        "forma_pagamento": "Pix",
        "conta_cartao": "Banco do Brasil",
    }
    dados.update(overrides)
    return json.dumps(dados)


def json_consulta_valida(**overrides):
    dados = {"intencao": "consultar", "mes": "08", "ano": "2026"}
    dados.update(overrides)
    return json.dumps(dados)


def test_montar_system_prompt_inclui_data_categorias_e_estruturas(monkeypatch):
    monkeypatch.setattr(ai_service, "datetime", DataFixa)

    prompt = ai_service.montar_system_prompt(["Feira", "Outros"])

    assert "A data de hoje é 21/08/2026" in prompt
    assert "O ano é 2026" in prompt
    assert "['Feira', 'Outros']" in prompt
    assert '"intencao": "registrar"' in prompt
    assert '"intencao": "consultar"' in prompt
    assert "Não retorne Markdown" in prompt
    assert "forma_pagamento" in prompt
    assert "Crédito" in prompt
    assert "Alimentação" in prompt
    assert '"conta_cartao"' in prompt
    assert 'conta_cartao "Nubank"' in prompt
    assert '"Pix" e "Banco do Brasil"' in prompt
    assert '"Débito" e "Banco do Brasil"' in prompt
    assert '"Dinheiro" nos dois campos' in prompt


def test_montar_system_prompt_distingue_compra_nova_de_parcela_corrente(monkeypatch):
    monkeypatch.setattr(ai_service, "datetime", DataFixa)

    prompt = ai_service.montar_system_prompt(["Outros"])

    assert '"2ª parcela de 5"' in prompt
    assert '"parcela atual"' in prompt
    assert '"Comprei um tênis de R$ 300 em 3x no Nubank"' in prompt
    assert '"Estou pagando R$ 100 referente à 2ª parcela de 3' in prompt
    assert "valor_total=300 e parcelas=3" in prompt
    assert "valor_total=100 e parcelas=1" in prompt


def test_validar_resposta_gemini_retorna_registro_financeiro_valido():
    resultado = ai_service.validar_resposta_gemini(json_registro_valido())

    assert resultado == RegistroFinanceiro(
        data="21/08/2026",
        tipo="gasto",
        valor_total=100.0,
        descricao="Mercado",
        parcelas=1,
        categoria="Outros",
        forma_pagamento="Pix",
        conta_cartao="Banco do Brasil",
    )


def test_validar_resposta_gemini_retorna_consulta_valida():
    resultado = ai_service.validar_resposta_gemini(json_consulta_valida())

    assert resultado == {"intencao": "consultar", "mes": "08", "ano": "2026"}


@pytest.mark.parametrize("conteudo", ["{", "", None])
def test_validar_resposta_gemini_rejeita_json_invalido_ou_vazio(conteudo):
    with pytest.raises(InterpretacaoIAError, match="JSON válido"):
        ai_service.validar_resposta_gemini(conteudo)


def test_validar_resposta_gemini_rejeita_json_que_nao_eh_objeto():
    with pytest.raises(InterpretacaoIAError, match="não retornou um objeto"):
        ai_service.validar_resposta_gemini("[]")


def test_validar_resposta_gemini_rejeita_intencao_desconhecida():
    with pytest.raises(InterpretacaoIAError, match="intenção desconhecida"):
        ai_service.validar_resposta_gemini(json.dumps({"intencao": "investir"}))


def test_validar_resposta_gemini_rejeita_chaves_ausentes_em_registro():
    dados = json.loads(json_registro_valido())
    dados.pop("categoria")

    with pytest.raises(InterpretacaoIAError, match="registro fora do padrão"):
        ai_service.validar_resposta_gemini(json.dumps(dados))


def test_validar_resposta_gemini_rejeita_registro_sem_forma_pagamento():
    dados = json.loads(json_registro_valido())
    dados.pop("forma_pagamento")

    with pytest.raises(InterpretacaoIAError, match="registro fora do padrão"):
        ai_service.validar_resposta_gemini(json.dumps(dados))


def test_validar_resposta_gemini_rejeita_registro_sem_conta_cartao():
    dados = json.loads(json_registro_valido())
    dados.pop("conta_cartao")

    with pytest.raises(InterpretacaoIAError, match="registro fora do padrão"):
        ai_service.validar_resposta_gemini(json.dumps(dados))


@pytest.mark.parametrize(
    ("forma_pagamento", "conta_cartao"),
    [
        ("Crédito", "Nubank"),
        ("Crédito", "Banco do Brasil"),
        ("Pix", "Banco do Brasil"),
        ("Débito", "Banco do Brasil"),
        ("Dinheiro", "Dinheiro"),
    ],
)
def test_validar_resposta_gemini_aceita_forma_e_conta_cartao(
    forma_pagamento, conta_cartao
):
    resultado = ai_service.validar_resposta_gemini(
        json_registro_valido(forma_pagamento=forma_pagamento, conta_cartao=conta_cartao)
    )

    assert resultado.forma_pagamento == forma_pagamento
    assert resultado.conta_cartao == conta_cartao


def test_validar_resposta_gemini_rejeita_conta_cartao_invalido():
    with pytest.raises(EntradaInvalidaError, match="Conta/Cartão inválido"):
        ai_service.validar_resposta_gemini(
            json_registro_valido(conta_cartao="Banco desconhecido")
        )


@pytest.mark.parametrize(
    ("texto", "valor_total", "parcelas"),
    [
        ("paguei R$ 100 referente à 2ª parcela de 5 no Banco do Brasil", 100, 5),
        ("paguei R$ 49,25 da 4ª e última parcela no Banco do Brasil", 49.25, 4),
        ("paguei 100 da 2a parcela de 5", 100, 5),
        ("paguei 100 da segunda parcela de 5", 100, 5),
        ("paguei 100 da 4ª parcela de 4", 100, 4),
        ("paguei 100 da última parcela", 100, 4),
        ("paguei 100 da parcela atual", 100, 5),
    ],
)
def test_interpretar_mensagem_corrige_parcela_existente_mesmo_com_erro_do_gemini(
    monkeypatch, texto, valor_total, parcelas
):
    resposta = SimpleNamespace(
        text=json_registro_valido(valor_total=valor_total, parcelas=parcelas)
    )
    generate_content = Mock(return_value=resposta)
    monkeypatch.setattr(ai_service.client.models, "generate_content", generate_content)

    resultado = ai_service.interpretar_mensagem(texto)

    assert resultado.parcelas == 1
    assert resultado.valor_total == valor_total
    assert resultado.conta_cartao == "Banco do Brasil"
    generate_content.assert_called_once()


def test_interpretar_mensagem_preserva_nova_compra_parcelada(monkeypatch):
    resposta = SimpleNamespace(
        text=json_registro_valido(
            valor_total=300,
            parcelas=3,
            forma_pagamento="Crédito",
            conta_cartao="Nubank",
        )
    )
    monkeypatch.setattr(
        ai_service.client.models, "generate_content", Mock(return_value=resposta)
    )

    resultado = ai_service.interpretar_mensagem(
        "comprei um tênis de R$ 300 em 3x no Nubank"
    )

    assert resultado.valor_total == 300
    assert resultado.parcelas == 3
    assert resultado.conta_cartao == "Nubank"


def test_validar_resposta_gemini_rejeita_chaves_extras_em_registro():
    with pytest.raises(InterpretacaoIAError, match="registro fora do padrão"):
        ai_service.validar_resposta_gemini(json_registro_valido(observacao="extra"))


def test_validar_resposta_gemini_rejeita_chaves_ausentes_em_consulta():
    with pytest.raises(InterpretacaoIAError, match="consulta fora do padrão"):
        ai_service.validar_resposta_gemini(json.dumps({"intencao": "consultar"}))


def test_validar_resposta_gemini_rejeita_chaves_extras_em_consulta():
    with pytest.raises(InterpretacaoIAError, match="consulta fora do padrão"):
        ai_service.validar_resposta_gemini(json_consulta_valida(dia="21"))


def test_validar_resposta_gemini_rejeita_campos_obrigatorios_vazios():
    with pytest.raises(InterpretacaoIAError, match="registro incompleta"):
        ai_service.validar_resposta_gemini(json_registro_valido(descricao=""))


def test_validar_resposta_gemini_rejeita_registro_que_falha_na_conversao():
    with pytest.raises(InterpretacaoIAError, match="não pôde ser convertida"):
        ai_service.validar_resposta_gemini(json_registro_valido(parcelas="duas"))


def test_validar_resposta_gemini_propaga_erro_de_validacao_do_registro(monkeypatch):
    erro = EntradaInvalidaError("registro inválido")
    validar_registro = Mock(side_effect=erro)
    monkeypatch.setattr(ai_service, "validar_registro", validar_registro)

    with pytest.raises(EntradaInvalidaError, match="registro inválido"):
        ai_service.validar_resposta_gemini(json_registro_valido())

    validar_registro.assert_called_once()


def test_validar_resposta_gemini_aceita_chaves_exatas_sem_campos_extras():
    resultado = ai_service.validar_resposta_gemini(json_registro_valido(parcelas="2"))

    assert isinstance(resultado, RegistroFinanceiro)
    assert resultado.parcelas == 2
    assert resultado.forma_pagamento == "Pix"
    assert resultado.conta_cartao == "Banco do Brasil"


def test_interpretar_mensagem_chama_gemini_e_retorna_registro(monkeypatch):
    resposta = SimpleNamespace(text=json_registro_valido(valor_total=42.5))
    generate_content = Mock(return_value=resposta)
    monkeypatch.setattr(ai_service.client.models, "generate_content", generate_content)

    resultado = ai_service.interpretar_mensagem("gastei 42.50 no mercado")

    assert isinstance(resultado, RegistroFinanceiro)
    assert resultado.valor_total == 42.5
    generate_content.assert_called_once()
    argumentos = generate_content.call_args.kwargs
    assert argumentos["model"] == "gemini-2.5-flash"
    assert argumentos["contents"] == "gastei 42.50 no mercado"
    assert argumentos["config"].response_mime_type == "application/json"


def test_interpretar_mensagem_chama_gemini_e_retorna_consulta(monkeypatch):
    resposta = SimpleNamespace(text=json_consulta_valida())
    generate_content = Mock(return_value=resposta)
    monkeypatch.setattr(ai_service.client.models, "generate_content", generate_content)

    resultado = ai_service.interpretar_mensagem("quanto gastei este mes?")

    assert resultado == {"intencao": "consultar", "mes": "08", "ano": "2026"}
    generate_content.assert_called_once()


def test_interpretar_mensagem_propaga_erro_do_cliente_gemini(monkeypatch):
    generate_content = Mock(side_effect=RuntimeError("falha no cliente"))
    monkeypatch.setattr(ai_service.client.models, "generate_content", generate_content)

    with pytest.raises(RuntimeError, match="falha no cliente"):
        ai_service.interpretar_mensagem("mensagem ficticia")


def test_logs_nao_expoem_dados_sensiveis(monkeypatch, caplog):
    texto_usuario = "paguei 987654321 no mercado secreto"
    resposta_bruta = json_registro_valido(valor_total=987654321, descricao="secreto")
    resposta = SimpleNamespace(text=resposta_bruta)
    monkeypatch.setattr(
        ai_service.client.models,
        "generate_content",
        Mock(return_value=resposta),
    )

    with caplog.at_level("INFO", logger="ai_service"):
        ai_service.interpretar_mensagem(texto_usuario)

    assert texto_usuario not in caplog.text
    assert "987654321" not in caplog.text
    assert resposta_bruta not in caplog.text
    assert "gemini-api-key-ficticia" not in caplog.text
