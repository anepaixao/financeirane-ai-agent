import logging
import os

from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
AUTHORIZED_CHAT_IDS_RAW = os.getenv("AUTHORIZED_CHAT_IDS", "")
APP_ENV = os.getenv("APP_ENV", "development").strip().lower()

GOOGLE_CREDENTIALS_FILE = os.getenv("GOOGLE_CREDENTIALS_FILE", "credenciais.json")
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID", "").strip()
SPREADSHEET_NAME = os.getenv("SPREADSHEET_NAME", "Financeirane")

AMBIENTES_PERMITIDOS = {"development", "production"}
CATEGORIAS_PERMITIDAS = [
    "Alimentação",
    "Feira",
    "Transporte",
    "Lazer",
    "Vestuário",
    "Eletrônicos",
    "Educação",
    "Saúde",
    "Moradia",
    "Assinaturas",
    "Outros",
]
FORMAS_PAGAMENTO_PERMITIDAS = ["Crédito", "Débito", "Pix", "Dinheiro"]
TIPOS_PERMITIDOS = {"gasto", "receita"}
MAX_MESSAGE_LENGTH = 1000
MAX_PARCELAS = 120


def parse_authorized_chat_ids(raw_chat_ids):
    try:
        return {
            int(chat_id.strip())
            for chat_id in raw_chat_ids.split(",")
            if chat_id.strip()
        }
    except ValueError as exc:
        raise RuntimeError(
            "AUTHORIZED_CHAT_IDS deve conter apenas IDs numéricos separados por vírgula"
        ) from exc


def validate_required_settings():
    if APP_ENV not in AMBIENTES_PERMITIDOS:
        ambientes = ", ".join(sorted(AMBIENTES_PERMITIDOS))
        raise RuntimeError(
            f"APP_ENV inválido: {APP_ENV}. Use um destes valores: {ambientes}."
        )

    if APP_ENV == "production" and not SPREADSHEET_ID:
        raise RuntimeError("SPREADSHEET_ID é obrigatório quando APP_ENV=production.")

    if not TELEGRAM_TOKEN:
        raise RuntimeError("TELEGRAM_TOKEN não encontrado no arquivo .env")

    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY não encontrado no arquivo .env")


validate_required_settings()
AUTHORIZED_CHAT_IDS = parse_authorized_chat_ids(AUTHORIZED_CHAT_IDS_RAW)

if not AUTHORIZED_CHAT_IDS:
    logger.warning(
        "AUTHORIZED_CHAT_IDS não configurado. O bot ignorará mensagens de todos os usuários."
    )
