import json
import logging
from datetime import datetime

from google import genai
from google.genai import types

from config import CATEGORIAS_PERMITIDAS, GEMINI_API_KEY


client = genai.Client(api_key=GEMINI_API_KEY)
logger = logging.getLogger(__name__)

CHAVES_REGISTRO = {"intencao", "data", "tipo", "valor_total", "descricao", "parcelas", "categoria"}
CHAVES_CONSULTA = {"intencao", "mes", "ano"}


class RespostaGeminiInvalidaError(Exception):
    pass


def montar_system_prompt(categorias):
    hoje = datetime.today()

    return f"""
Você é a Financeirane, uma assistente financeira pessoal exclusiva da utilizadora.
A data de hoje é {hoje.strftime("%d/%m/%Y")}. O ano é {hoje.year}.

As categorias permitidas para os gastos são estritamente estas: {categorias}. Use a sua inteligência para classificar o gasto na categoria mais adequada da vida pessoal dela. Se não se encaixar em nenhuma, use "Outros". Se for uma receita/ganho, use "Outros".

Analise a mensagem e retorne ESTRITAMENTE um único objeto JSON válido.
Não retorne Markdown, comentários, texto explicativo, aspas externas, blocos de código ou campos extras.
O JSON deve conter exatamente uma das estruturas abaixo.

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


def validar_resposta_gemini(conteudo):
    try:
        dados = json.loads(conteudo)
    except (TypeError, json.JSONDecodeError) as exc:
        raise RespostaGeminiInvalidaError("Gemini retornou uma resposta que não é um JSON válido.") from exc

    if not isinstance(dados, dict):
        raise RespostaGeminiInvalidaError("Gemini retornou JSON válido, mas não retornou um objeto.")

    intencao = dados.get("intencao")

    if intencao == "registrar":
        chaves_recebidas = set(dados.keys())
        if chaves_recebidas != CHAVES_REGISTRO:
            raise RespostaGeminiInvalidaError(
                "Resposta de registro fora do padrão. "
                f"Chaves esperadas: {sorted(CHAVES_REGISTRO)}. "
                f"Chaves recebidas: {sorted(chaves_recebidas)}."
            )

        if not dados.get("categoria") or dados.get("valor_total") is None or not dados.get("descricao"):
            raise RespostaGeminiInvalidaError(
                "Resposta de registro incompleta. Campos obrigatórios: categoria, valor_total e descricao."
            )

        return dados

    if intencao == "consultar":
        chaves_recebidas = set(dados.keys())
        if chaves_recebidas != CHAVES_CONSULTA:
            raise RespostaGeminiInvalidaError(
                "Resposta de consulta fora do padrão. "
                f"Chaves esperadas: {sorted(CHAVES_CONSULTA)}. "
                f"Chaves recebidas: {sorted(chaves_recebidas)}."
            )

        return dados

    raise RespostaGeminiInvalidaError("Gemini retornou uma intenção desconhecida ou ausente.")


def interpretar_mensagem(texto):
    logger.info("Enviando mensagem autorizada para interpretação da IA.")
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=texto,
        config=types.GenerateContentConfig(
            system_instruction=montar_system_prompt(CATEGORIAS_PERMITIDAS),
            response_mime_type="application/json",
        ),
    )
    dados = validar_resposta_gemini(response.text)
    logger.info("Resposta da IA validada com sucesso. intencao=%s", dados.get("intencao"))
    return dados
