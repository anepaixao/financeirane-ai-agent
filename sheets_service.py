import calendar
import logging
import time
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal

import gspread
from gspread.exceptions import APIError

from config import (
    CATEGORIAS_PERMITIDAS,
    GOOGLE_CREDENTIALS_FILE,
    MAX_PARCELAS,
    SPREADSHEET_NAME,
    TIPOS_PERMITIDOS,
)
from logging_config import duracao_ms, iniciar_medicao

MAX_TENTATIVAS_ESCRITA = 3
TEMPO_ESPERA_INICIAL = 2
STATUS_TRANSIENTES = {408, 429, 500, 502, 503, 504}
logger = logging.getLogger(__name__)
CENTAVOS_POR_REAL = Decimal("100")


class PlanilhaEscritaError(Exception):
    pass


def conectar_planilha():
    inicio = iniciar_medicao()
    logger.info("Conectando ao Google Planilhas. operacao=conectar_planilha")
    gc = gspread.service_account(filename=GOOGLE_CREDENTIALS_FILE)
    planilha = gc.open(SPREADSHEET_NAME).sheet1
    logger.info(
        "Conectado à planilha configurada. operacao=conectar_planilha duracao_ms=%s",
        duracao_ms(inicio),
    )
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


def valor_em_centavos(valor):
    return int(
        (Decimal(str(valor)) * CENTAVOS_POR_REAL).quantize(
            Decimal("1"), rounding=ROUND_HALF_UP
        )
    )


def formatar_centavos(valor_centavos):
    reais, centavos = divmod(valor_centavos, 100)
    return f"{reais},{centavos:02d}"


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
    inicio = iniciar_medicao()

    for tentativa in range(1, MAX_TENTATIVAS_ESCRITA + 1):
        try:
            planilha.insert_rows(linhas, row=index)
            logger.info(
                "Lote escrito no Google Sheets. operacao=inserir_linhas tentativa=%s total_linhas=%s duracao_ms=%s",
                tentativa,
                len(linhas),
                duracao_ms(inicio),
            )
            return
        except Exception as exc:
            ultima_excecao = exc

            if not erro_transiente_google(exc) or tentativa == MAX_TENTATIVAS_ESCRITA:
                logger.exception(
                    "Falha definitiva ao escrever lote no Google Sheets. operacao=inserir_linhas tentativa=%s total_linhas=%s erro=%s duracao_ms=%s",
                    tentativa,
                    len(linhas),
                    exc.__class__.__name__,
                    duracao_ms(inicio),
                )
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

    raise PlanilhaEscritaError(
        "Falha inesperada ao escrever lote na planilha."
    ) from ultima_excecao


def registrar_movimentacao(planilha, dados):
    data_original = dados.data

    tipo = dados.tipo

    raw_valor = dados.valor_total
    logger.debug(
        "Valor recebido da IA para registro. operacao=preparar_registro tipo_python=%s",
        type(raw_valor).__name__,
    )
    valor_total = float(raw_valor)
    if valor_total <= 0:
        raise ValueError("valor_total deve ser maior que zero")

    descricao_original = texto_seguro_planilha(dados.descricao)
    total_parcelas = int(dados.parcelas)
    if total_parcelas < 1 or total_parcelas > MAX_PARCELAS:
        raise ValueError(f"parcelas deve estar entre 1 e {MAX_PARCELAS}")
    categoria = dados.categoria

    valor_total_centavos = valor_em_centavos(raw_valor)
    valor_base_centavos, centavos_restantes = divmod(
        valor_total_centavos, total_parcelas
    )

    logger.info(
        "Preparando escrita na planilha. operacao=registrar_movimentacao parcelas=%s tipo=%s",
        total_parcelas,
        tipo,
    )
    linha_insercao = 2
    novas_linhas = []

    for i in range(total_parcelas):
        valor_parcela_centavos = valor_base_centavos + (
            1 if i < centavos_restantes else 0
        )
        valor_formatado = formatar_centavos(valor_parcela_centavos)
        data_parcela = calcular_data_parcela(data_original, i)
        descricao_final = (
            f"{descricao_original} (Parcela {i + 1}/{total_parcelas})"
            if total_parcelas > 1
            else descricao_original
        )
        novas_linhas.append(
            [
                data_parcela,
                tipo,
                valor_formatado,
                descricao_final,
                total_parcelas,
                categoria,
            ]
        )

    inserir_linhas_com_retry(planilha, novas_linhas, linha_insercao)
    logger.info(
        "Movimentação salva na planilha. operacao=registrar_movimentacao total_linhas=%s",
        len(novas_linhas),
    )

    if total_parcelas > 1:
        return f"✅ Registado!\nCompra de R$ {valor_total:.2f} ({categoria}) dividida em {total_parcelas}x lançada na planilha."
    return f"✅ Registado!\nAdicionado: {descricao_original} ({categoria}) - R$ {valor_total:.2f}."


def consultar_gastos_mes(planilha, mes_alvo, ano_alvo):
    inicio = iniciar_medicao()
    logger.info(
        "Buscando gastos para período. operacao=consultar_gastos_mes mes=%s ano=%s",
        mes_alvo,
        ano_alvo,
    )

    todas_as_linhas = planilha.get_all_values()[1:]
    logger.info(
        "Linhas lidas da planilha. operacao=consultar_gastos_mes total_linhas=%s duracao_ms=%s",
        len(todas_as_linhas),
        duracao_ms(inicio),
    )

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
                    detalhes_gastos.append(
                        f"• [{cat_linha}] {desc_linha}: R$ {valor_num:.2f}"
                    )
        except Exception as exc:
            logger.debug(
                "Linha ignorada durante consulta. operacao=consultar_gastos_mes erro=%s",
                exc.__class__.__name__,
            )
            continue

    if total_gastos > 0:
        resposta = f"📊 *Resumo de Contas ({mes_alvo}/{ano_alvo})*\n\n"
        resposta += "\n".join(detalhes_gastos)
        resposta += f"\n\n💰 *Total a pagar neste mês: R$ {total_gastos:.2f}*"
        return resposta

    return f"🔍 Não encontrei nenhum gasto registado para o mês {mes_alvo}/{ano_alvo}."
