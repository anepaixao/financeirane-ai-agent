import importlib
import sys

import pytest


def importar_config(monkeypatch, **env):
    monkeypatch.setenv("TELEGRAM_TOKEN", "token-de-teste")
    monkeypatch.setenv("GEMINI_API_KEY", "chave-de-teste")
    monkeypatch.setenv("AUTHORIZED_CHAT_IDS", "123456789")
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.delenv("SPREADSHEET_ID", raising=False)

    for chave, valor in env.items():
        if valor is None:
            monkeypatch.delenv(chave, raising=False)
        else:
            monkeypatch.setenv(chave, valor)

    sys.modules.pop("config", None)
    sys.modules.pop("financeirane.config", None)
    return importlib.import_module("config")


@pytest.fixture
def config_module(monkeypatch):
    """Importa config.py com variáveis seguras e independentes do .env real."""
    module = importar_config(monkeypatch)
    yield module

    sys.modules.pop("config", None)
    sys.modules.pop("financeirane.config", None)


def test_parse_authorized_chat_ids_retorna_conjunto_vazio(config_module):
    assert config_module.parse_authorized_chat_ids("") == set()


def test_parse_authorized_chat_ids_converte_um_id(config_module):
    assert config_module.parse_authorized_chat_ids("123456789") == {123456789}


def test_parse_authorized_chat_ids_converte_varios_ids(config_module):
    resultado = config_module.parse_authorized_chat_ids("123456789,987654321")

    assert resultado == {123456789, 987654321}


def test_parse_authorized_chat_ids_ignora_espacos(config_module):
    resultado = config_module.parse_authorized_chat_ids(" 123456789 , 987654321 ")

    assert resultado == {123456789, 987654321}


def test_parse_authorized_chat_ids_elimina_ids_duplicados(config_module):
    resultado = config_module.parse_authorized_chat_ids("123456789,123456789")

    assert resultado == {123456789}


def test_parse_authorized_chat_ids_ignora_itens_vazios(config_module):
    resultado = config_module.parse_authorized_chat_ids("123456789,, ,987654321,")

    assert resultado == {123456789, 987654321}


def test_parse_authorized_chat_ids_rejeita_valor_nao_numerico(config_module):
    with pytest.raises(
        RuntimeError,
        match="AUTHORIZED_CHAT_IDS deve conter apenas IDs numéricos",
    ):
        config_module.parse_authorized_chat_ids("123456789,ane")


def test_app_env_default_development(monkeypatch):
    module = importar_config(monkeypatch)

    assert module.APP_ENV == "development"


def test_app_env_production_sem_spreadsheet_id_falha(monkeypatch):
    with pytest.raises(RuntimeError, match="SPREADSHEET_ID é obrigatório"):
        importar_config(monkeypatch, APP_ENV="production", SPREADSHEET_ID=None)


def test_app_env_invalido_falha(monkeypatch):
    with pytest.raises(RuntimeError, match="APP_ENV inválido"):
        importar_config(monkeypatch, APP_ENV="staging")


def test_app_env_production_com_spreadsheet_id_eh_valido(monkeypatch):
    module = importar_config(
        monkeypatch, APP_ENV="production", SPREADSHEET_ID="spreadsheet-id-ficticio"
    )

    assert module.APP_ENV == "production"
    assert module.SPREADSHEET_ID == "spreadsheet-id-ficticio"
