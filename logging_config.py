import logging
import os
from time import perf_counter

LOG_LEVEL_ENV = "LOG_LEVEL"
DEFAULT_LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
NIVEIS_VALIDOS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}


def obter_log_level(valor=None):
    nivel = str(
        valor if valor is not None else os.getenv(LOG_LEVEL_ENV, DEFAULT_LOG_LEVEL)
    )
    nivel = nivel.strip().upper()
    return nivel if nivel in NIVEIS_VALIDOS else DEFAULT_LOG_LEVEL


def configurar_logging():
    logging.basicConfig(
        level=getattr(logging, obter_log_level()),
        format=LOG_FORMAT,
        force=True,
    )


def mascarar_id(identificador):
    if identificador is None:
        return "ausente"

    texto = str(identificador)
    if len(texto) <= 4:
        return "*" * len(texto)

    return f"{'*' * (len(texto) - 4)}{texto[-4:]}"


def iniciar_medicao():
    return perf_counter()


def duracao_ms(inicio):
    return round((perf_counter() - inicio) * 1000, 2)
