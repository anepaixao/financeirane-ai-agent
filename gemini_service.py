import json
from datetime import datetime

from google import genai
from google.genai import types

from config import CATEGORIAS_PERMITIDAS, GEMINI_API_KEY


client = genai.Client(api_key=GEMINI_API_KEY)

SYSTEM_PROMPT = f"""
Você é a Financeirane, uma assistente financeira pessoal exclusiva da utilizadora.
A data de hoje é {datetime.today().strftime("%d/%m/%Y")}. O ano é 2026.

As categorias permitidas para os gastos são estritamente estas: {CATEGORIAS_PERMITIDAS}. Use a sua inteligência para classificar o gasto na categoria mais adequada da vida pessoal dela. Se não se encaixar em nenhuma, use "Outros". Se for uma receita/ganho, use "Outros".

Analise a mensagem e retorne ESTRITAMENTE um objeto JSON com o seguinte formato:

Se for para REGISTRAR um gasto ou receita:
{{
  "intencao": "registrar",
  "data": "DD/MM/AAAA",
  "tipo": "gasto" ou "receita",
  "valor_total": número real,
  "descricao": "resumo do gasto",
  "parcelas": número inteiro,
  "categoria": "uma das categorias da lista"
}}

Se for para CONSULTAR ou perguntar quanto tem para pagar/gasto:
{{
  "intencao": "consultar",
  "mes": "MM",
  "ano": "AAAA"
}}
"""


def interpretar_mensagem(texto):
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=texto,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            response_mime_type="application/json",
        ),
    )
    print(f"🧠 2. Resposta bruta da IA:\n{response.text}")
    return json.loads(response.text)
