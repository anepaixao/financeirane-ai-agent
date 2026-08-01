import json
import logging
from datetime import datetime

from google import genai
from google.genai import types

from config import CATEGORIAS_PERMITIDAS, GEMINI_API_KEY
from exceptions import InterpretacaoIAError
from logging_config import duracao_ms, iniciar_medicao
from models import RegistroFinanceiro
from validators import validar_registro

client = genai.Client(api_key=GEMINI_API_KEY)
logger = logging.getLogger(__name__)

CHAVES_REGISTRO = {
    "intencao",
    "data",
    "tipo",
    "valor_total",
    "descricao",
    "parcelas",
    "categoria",
}
CHAVES_CONSULTA = {"intencao", "mes", "ano"}


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
        raise InterpretacaoIAError(
            "Gemini retornou uma resposta que não é um JSON válido."
        ) from exc

    if not isinstance(dados, dict):
        raise InterpretacaoIAError(
            "Gemini retornou JSON válido, mas não retornou um objeto."
        )

    intencao = dados.get("intencao")

    if intencao == "registrar":
        chaves_recebidas = set(dados.keys())
        if chaves_recebidas != CHAVES_REGISTRO:
            raise InterpretacaoIAError(
                "Resposta de registro fora do padrão. "
                f"Chaves esperadas: {sorted(CHAVES_REGISTRO)}. "
                f"Chaves recebidas: {sorted(chaves_recebidas)}."
            )

        if (
            not dados.get("categoria")
            or dados.get("valor_total") is None
            or not dados.get("descricao")
        ):
            raise InterpretacaoIAError(
                "Resposta de registro incompleta. Campos obrigatórios: categoria, valor_total e descricao."
            )

        try:
            registro = RegistroFinanceiro(
                data=dados["data"],
                tipo=dados["tipo"],
                valor_total=float(dados["valor_total"]),
                descricao=dados["descricao"],
                parcelas=int(dados["parcelas"]),
                categoria=dados["categoria"],
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise InterpretacaoIAError(
                "Resposta de registro não pôde ser convertida em RegistroFinanceiro."
            ) from exc

        return validar_registro(registro)

    if intencao == "consultar":
        chaves_recebidas = set(dados.keys())
        if chaves_recebidas != CHAVES_CONSULTA:
            raise InterpretacaoIAError(
                "Resposta de consulta fora do padrão. "
                f"Chaves esperadas: {sorted(CHAVES_CONSULTA)}. "
                f"Chaves recebidas: {sorted(chaves_recebidas)}."
            )

        return dados

    raise InterpretacaoIAError("Gemini retornou uma intenção desconhecida ou ausente.")


def interpretar_mensagem(texto):
    inicio = iniciar_medicao()
    modelo = "gemini-2.5-flash"
    logger.info(
        "Enviando mensagem autorizada para interpretação da IA. operacao=gemini_generate modelo=%s",
        modelo,
    )
    try:
        response = client.models.generate_content(
            model=modelo,
            contents=texto,
            config=types.GenerateContentConfig(
                system_instruction=montar_system_prompt(CATEGORIAS_PERMITIDAS),
                response_mime_type="application/json",
            ),
        )
        dados = validar_resposta_gemini(response.text)
    except Exception as exc:
        logger.exception(
            "Erro ao interpretar mensagem com Gemini. operacao=gemini_generate modelo=%s erro=%s duracao_ms=%s",
            modelo,
            exc.__class__.__name__,
            duracao_ms(inicio),
        )
        raise

    if isinstance(dados, RegistroFinanceiro):
        logger.info(
            "Resposta da IA validada com sucesso. operacao=validar_resposta_gemini intencao=registrar duracao_ms=%s",
            duracao_ms(inicio),
        )
    else:
        logger.info(
            "Resposta da IA validada com sucesso. operacao=validar_resposta_gemini intencao=%s duracao_ms=%s",
            dados.get("intencao"),
            duracao_ms(inicio),
        )
    return dados
