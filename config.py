import os

from dotenv import load_dotenv


load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
AUTHORIZED_CHAT_IDS_RAW = os.getenv("AUTHORIZED_CHAT_IDS", "")

GOOGLE_CREDENTIALS_FILE = os.getenv("GOOGLE_CREDENTIALS_FILE", "credenciais.json")
SPREADSHEET_NAME = os.getenv("SPREADSHEET_NAME", "Financeirane")

CATEGORIAS_PERMITIDAS = [
    "Cartão de Crédito",
    "Aluguel",
    "Feira",
    "Internet",
    "Transporte",
    "Lazer",
    "Saúde",
    "Educação",
    "Outros",
]
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
        raise RuntimeError("AUTHORIZED_CHAT_IDS deve conter apenas IDs numéricos separados por vírgula") from exc


def validate_required_settings():
    if not TELEGRAM_TOKEN:
        raise RuntimeError("TELEGRAM_TOKEN não encontrado no arquivo .env")

    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY não encontrado no arquivo .env")


validate_required_settings()
AUTHORIZED_CHAT_IDS = parse_authorized_chat_ids(AUTHORIZED_CHAT_IDS_RAW)

if not AUTHORIZED_CHAT_IDS:
    print("⚠️ AUTHORIZED_CHAT_IDS não configurado. O bot só responderá /id e /meu_id.")
