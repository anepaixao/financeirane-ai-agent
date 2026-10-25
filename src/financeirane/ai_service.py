import json
import logging
import re
import unicodedata
from dataclasses import replace
from datetime import datetime

from google import genai
from google.genai import types

from financeirane.config import (
    CATEGORIAS_PERMITIDAS,
    CONTAS_CARTOES_PERMITIDOS,
    FORMAS_PAGAMENTO_PERMITIDAS,
    GEMINI_API_KEY,
)
from financeirane.domain.exceptions import InterpretacaoIAError
from financeirane.domain.models import RegistroFinanceiro
from financeirane.domain.validators import validar_registro
from financeirane.logging_config import duracao_ms, iniciar_medicao

client = genai.Client(api_key=GEMINI_API_KEY)
logger = logging.getLogger("ai_service")

CHAVES_REGISTRO = {
    "intencao",
    "data",
    "tipo",
    "valor_total",
    "descricao",
    "parcelas",
    "categoria",
    "forma_pagamento",
    "conta_cartao",
}
CHAVES_CONSULTA = {"intencao", "mes", "ano"}
PARCELA_EXISTENTE = re.compile(
    r"\b(?:\d+\s*[ao]?|segunda)\s+(?:e\s+ultima\s+)?parcela\b"
    r"|\bultima\s+parcela\b"
    r"|\bparcela\s+atual\b"
)


def informa_parcela_existente(texto):
    texto_normalizado = "".join(
        caractere
        for caractere in unicodedata.normalize("NFKD", texto.casefold())
        if not unicodedata.combining(caractere)
    )
    return PARCELA_EXISTENTE.search(texto_normalizado) is not None


def montar_system_prompt(
    categorias,
    formas_pagamento=FORMAS_PAGAMENTO_PERMITIDAS,
    contas_cartoes=CONTAS_CARTOES_PERMITIDOS,
):
    hoje = datetime.today()

    return f"""
Você é a Financeirane, uma assistente financeira pessoal exclusiva da utilizadora.
A data de hoje é {hoje.strftime("%d/%m/%Y")}. O ano é {hoje.year}.

As categorias permitidas para os gastos são estritamente estas: {categorias}. Use a sua inteligência para classificar o gasto na categoria mais adequada da vida pessoal dela. Se não se encaixar em nenhuma, use "Outros". Se for uma receita/ganho, use "Outros".
As formas de pagamento permitidas são estritamente estas: {formas_pagamento}. Para registros, escolha exatamente uma delas. Exemplos: "comprei um açaí de 15 reais no crédito" usa categoria "Alimentação" e forma_pagamento "Crédito"; "paguei 32 reais de Uber no pix" usa categoria "Transporte" e forma_pagamento "Pix"; "comprei uma camisa no débito" usa categoria "Vestuário" e forma_pagamento "Débito"; "paguei em dinheiro" usa forma_pagamento "Dinheiro".
forma_pagamento representa apenas o meio de pagamento: Crédito, Débito, Pix ou Dinheiro. conta_cartao representa a instituição, conta ou cartão utilizado e deve ser um destes valores: {contas_cartoes}. Não guarde o nome da conta/cartão apenas na descrição.
Exemplos: "gastei 20 reais no almoço no crédito do cartão Nubank" usa forma_pagamento "Crédito" e conta_cartao "Nubank"; "paguei 30 reais via Pix pelo Banco do Brasil" usa "Pix" e "Banco do Brasil"; "comprei um lanche no débito do Banco do Brasil" usa "Débito" e "Banco do Brasil"; "paguei 10 reais em dinheiro" usa "Dinheiro" nos dois campos.
Se o usuário disser que o valor informado é UMA parcela de compra já existente (por exemplo, "valor referente à 4ª parcela de 4", "2ª parcela de 5" ou "parcela atual"), use parcelas=1: o valor_total corresponde só à parcela corrente. Use parcelas > 1 somente para uma NOVA COMPRA cujo valor total será dividido. Exemplo: "Comprei um tênis de R$ 300 em 3x no Nubank" usa valor_total=300 e parcelas=3; "Estou pagando R$ 100 referente à 2ª parcela de 3 do tênis no Nubank" usa valor_total=100 e parcelas=1.

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
  "categoria": "uma das categorias da lista",
  "forma_pagamento": "uma das formas de pagamento da lista",
  "conta_cartao": "uma das contas/cartões da lista"
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
            or not dados.get("forma_pagamento")
            or not dados.get("conta_cartao")
            or dados.get("valor_total") is None
            or not dados.get("descricao")
        ):
            raise InterpretacaoIAError(
                "Resposta de registro incompleta. Campos obrigatórios: categoria, forma_pagamento, conta_cartao, valor_total e descricao."
            )

        try:
            registro = RegistroFinanceiro(
                data=dados["data"],
                tipo=dados["tipo"],
                valor_total=float(dados["valor_total"]),
                descricao=dados["descricao"],
                parcelas=int(dados["parcelas"]),
                categoria=dados["categoria"],
                forma_pagamento=dados["forma_pagamento"],
                conta_cartao=dados["conta_cartao"],
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
        if (
            isinstance(dados, RegistroFinanceiro)
            and dados.parcelas > 1
            and informa_parcela_existente(texto)
        ):
            dados = replace(dados, parcelas=1)
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
