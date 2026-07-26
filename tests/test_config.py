import importlib
import sys

import pytest


@pytest.fixture
def config_module(monkeypatch):
    """Importa config.py com variáveis seguras e independentes do .env real."""
    monkeypatch.setenv("TELEGRAM_TOKEN", "token-de-teste")
    monkeypatch.setenv("GEMINI_API_KEY", "chave-de-teste")
    monkeypatch.setenv("AUTHORIZED_CHAT_IDS", "123456789")

    sys.modules.pop("config", None)

    module = importlib.import_module("config")
    yield module

    sys.modules.pop("config", None)


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
