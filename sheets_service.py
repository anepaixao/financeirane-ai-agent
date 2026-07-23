import calendar
import logging
import time
from datetime import datetime

import gspread
from gspread.exceptions import APIError

from config import (
    CATEGORIAS_PERMITIDAS,
    GOOGLE_CREDENTIALS_FILE,
    MAX_PARCELAS,
    SPREADSHEET_NAME,
    TIPOS_PERMITIDOS,
)

MAX_TENTATIVAS_ESCRITA = 3
TEMPO_ESPERA_INICIAL = 2
STATUS_TRANSIENTES = {408, 429, 500, 502, 503, 504}
logger = logging.getLogger(__name__)


class PlanilhaEscritaError(Exception):
    pass


def conectar_planilha():
    logger.info("Conectando ao Google Planilhas.")
    gc = gspread.service_account(filename=GOOGLE_CREDENTIALS_FILE)
    planilha = gc.open(SPREADSHEET_NAME).sheet1
    logger.info("Conectado à planilha configurada.")
    return planilha


def calcular_data_parcela(data_original, meses_a_adicionar):
    data_base = datetime.strptime(data_original, "%d/%m/%Y")
    mes = data_base.month + meses_a_adicionar
    ano = data_base.year + (mes - 1) // 12
    mes = (mes - 1) % 12 + 1
    ultimo_dia = calendar.monthrange(ano, mes)[1]
    dia = min(data_base.day, ultimo_dia)
    return datetime(ano, mes, dia).strftime("%d/%m/%Y")


def texto_seguro_planilha(valor):
    texto = str(valor or "").replace("\n", " ").strip()
    if texto.startswith(("=", "+", "-", "@")):
        return f"'{texto}"
    return texto


def normalizar_categoria(categoria):
    return categoria if categoria in CATEGORIAS_PERMITIDAS else "Outros"


def normalizar_tipo(tipo):
    tipo_normalizado = str(tipo or "gasto").lower().strip()
    return tipo_normalizado if tipo_normalizado in TIPOS_PERMITIDOS else "gasto"


def obter_status_code_google(erro):
    resposta = getattr(erro, "response", None)
    if resposta is None:
        return None
    return getattr(resposta, "status_code", None)


def erro_transiente_google(erro):
    if isinstance(erro, APIError):
        status_code = obter_status_code_google(erro)
        return status_code in STATUS_TRANSIENTES

    nome_erro = erro.__class__.__name__.lower()
    return "timeout" in nome_erro or "connection" in nome_erro


def inserir_linhas_com_retry(planilha, linhas, index):
    ultima_excecao = None

    for tentativa in range(1, MAX_TENTATIVAS_ESCRITA + 1):
        try:
            planilha.insert_rows(linhas, row=index)
            return
        except Exception as exc:
            ultima_excecao = exc

            if not erro_transiente_google(exc) or tentativa == MAX_TENTATIVAS_ESCRITA:
                raise PlanilhaEscritaError(
                    f"Falha ao escrever lote na planilha após {tentativa} tentativa(s)."
                ) from exc

            tempo_espera = TEMPO_ESPERA_INICIAL * (2 ** (tentativa - 1))
            logger.warning(
                "Falha temporária ao escrever lote no Google Sheets. "
                "tentativa=%s/%s nova_tentativa_em=%ss erro=%s",
                tentativa,
                MAX_TENTATIVAS_ESCRITA,
                tempo_espera,
                exc.__class__.__name__,
            )
            time.sleep(tempo_espera)

    raise PlanilhaEscritaError("Falha inesperada ao escrever lote na planilha.") from ultima_excecao


def registrar_movimentacao(planilha, dados):
    data_original = dados.data

    if "2023" in data_original or "2024" in data_original or "2025" in data_original:
        dia_mes = data_original[:6]
        data_original = f"{dia_mes}2026"

    tipo = dados.tipo

    raw_valor = dados.valor_total
    logger.info("Valor recebido da IA para registro. tipo_python=%s", type(raw_valor).__name__)
    valor_total = float(raw_valor)
    if valor_total <= 0:
        raise ValueError("valor_total deve ser maior que zero")

    descricao_original = texto_seguro_planilha(dados.descricao)
    total_parcelas = int(dados.parcelas)
    if total_parcelas < 1 or total_parcelas > MAX_PARCELAS:
        raise ValueError(f"parcelas deve estar entre 1 e {MAX_PARCELAS}")
    categoria = dados.categoria

    valor_parcela = valor_total / total_parcelas
    valor_formatado = str(round(valor_parcela, 2)).replace(".", ",")

    logger.info("Preparando escrita na planilha. parcelas=%s tipo=%s categoria=%s", total_parcelas, tipo, categoria)
    linha_insercao = 2
    novas_linhas = []

    for i in range(total_parcelas):
        data_parcela = calcular_data_parcela(data_original, i)
        descricao_final = (
            f"{descricao_original} (Parcela {i + 1}/{total_parcelas})"
            if total_parcelas > 1
            else descricao_original
        )
        novas_linhas.append([data_parcela, tipo, valor_formatado, descricao_final, total_parcelas, categoria])

    inserir_linhas_com_retry(planilha, novas_linhas, linha_insercao)
    logger.info("Movimentação salva na planilha. total_linhas=%s", len(novas_linhas))

    if total_parcelas > 1:
        return f"✅ Registado!\nCompra de R$ {valor_total:.2f} ({categoria}) dividida em {total_parcelas}x lançada na planilha."
    return f"✅ Registado!\nAdicionado: {descricao_original} ({categoria}) - R$ {valor_total:.2f}."


def consultar_gastos_mes(planilha, mes_alvo, ano_alvo):
    logger.info("Buscando gastos para período. mes=%s ano=%s", mes_alvo, ano_alvo)

    todas_as_linhas = planilha.get_all_values()[1:]
    logger.info("Linhas lidas da planilha. total_linhas=%s", len(todas_as_linhas))

    total_gastos = 0.0
    detalhes_gastos = []

    for linha in todas_as_linhas:
        if len(linha) < 4:
            continue

        data_linha = linha[0]
        tipo_linha = linha[1]
        valor_linha = linha[2]
        desc_linha = linha[3]
        cat_linha = linha[5] if len(linha) >= 6 else "Outros"

        try:
            data_dt = datetime.strptime(data_linha, "%d/%m/%Y")
            if f"{data_dt.month:02d}" == mes_alvo and f"{data_dt.year}" == ano_alvo:
                if tipo_linha == "gasto":
                    valor_num = float(valor_linha.replace(",", "."))
                    total_gastos += valor_num
                    detalhes_gastos.append(f"• [{cat_linha}] {desc_linha}: R$ {valor_num:.2f}")
        except Exception:
            continue

    if total_gastos > 0:
        resposta = f"📊 *Resumo de Contas ({mes_alvo}/{ano_alvo})*\n\n"
        resposta += "\n".join(detalhes_gastos)
        resposta += f"\n\n💰 *Total a pagar neste mês: R$ {total_gastos:.2f}*"
        return resposta

    return f"🔍 Não encontrei nenhum gasto registado para o mês {mes_alvo}/{ano_alvo}."
