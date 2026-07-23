import logging
import os

from dotenv import load_dotenv
from google import genai


logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)

load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

logger.info("Buscando modelos disponíveis para a chave configurada.")

for modelo in client.models.list():
    logger.info("Modelo disponível: %s", modelo.name)
