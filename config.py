# Compatibilidade temporária durante a migração incremental para src layout.
from financeirane.config import (
    AUTHORIZED_CHAT_IDS,
    AUTHORIZED_CHAT_IDS_RAW,
    CATEGORIAS_PERMITIDAS,
    GEMINI_API_KEY,
    GOOGLE_CREDENTIALS_FILE,
    MAX_MESSAGE_LENGTH,
    MAX_PARCELAS,
    SPREADSHEET_NAME,
    TELEGRAM_TOKEN,
    TIPOS_PERMITIDOS,
    parse_authorized_chat_ids,
    validate_required_settings,
)

__all__ = [
    "AUTHORIZED_CHAT_IDS",
    "AUTHORIZED_CHAT_IDS_RAW",
    "CATEGORIAS_PERMITIDAS",
    "GEMINI_API_KEY",
    "GOOGLE_CREDENTIALS_FILE",
    "MAX_MESSAGE_LENGTH",
    "MAX_PARCELAS",
    "SPREADSHEET_NAME",
    "TELEGRAM_TOKEN",
    "TIPOS_PERMITIDOS",
    "parse_authorized_chat_ids",
    "validate_required_settings",
]
