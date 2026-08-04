import logging
from unittest.mock import Mock

import logging_config
from logging_config import (
    LOG_FORMAT,
    configurar_logging,
    duracao_ms,
    mascarar_id,
    obter_log_level,
)


def test_obter_log_level_retorna_info_por_padrao(monkeypatch):
    monkeypatch.delenv("LOG_LEVEL", raising=False)

    assert obter_log_level() == "INFO"


def test_obter_log_level_aceita_valor_valido(monkeypatch):
    monkeypatch.setenv("LOG_LEVEL", "debug")

    assert obter_log_level() == "DEBUG"


def test_obter_log_level_invalido_usa_fallback_seguro(monkeypatch):
    monkeypatch.setenv("LOG_LEVEL", "barulhento")

    assert obter_log_level() == "INFO"


def test_configurar_logging_aplica_nivel_esperado(monkeypatch):
    monkeypatch.setenv("LOG_LEVEL", "ERROR")
    basic_config = Mock()
    monkeypatch.setattr(logging, "basicConfig", basic_config)

    configurar_logging()

    basic_config.assert_called_once_with(
        level=logging.ERROR,
        format=LOG_FORMAT,
        force=True,
    )


def test_mascarar_id_nao_retorna_id_completo():
    assert mascarar_id(123456789) == "*****6789"


def test_mascarar_id_trata_valor_ausente():
    assert mascarar_id(None) == "ausente"


def test_duracao_ms_calcula_duracao_de_forma_deterministica(monkeypatch):
    monkeypatch.setattr(logging_config, "perf_counter", Mock(return_value=10.125))

    assert duracao_ms(10.0) == 125.0
