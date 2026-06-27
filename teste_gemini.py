import os
import logging
import google.generativeai as genai
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)

load_dotenv()
genai.configure(api_key=os.getenv('GEMINI_API_KEY'))

logger.info("Buscando modelos disponíveis para a chave configurada.")

# Lista todos os modelos que aceitam gerar texto
for m in genai.list_models():
    if 'generateContent' in m.supported_generation_methods:
        logger.info("Modelo disponível: %s", m.name)
