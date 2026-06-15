import calendar
from datetime import datetime

import gspread

from config import (
    CATEGORIAS_PERMITIDAS,
    GOOGLE_CREDENTIALS_FILE,
    MAX_PARCELAS,
    SPREADSHEET_NAME,
    TIPOS_PERMITIDOS,
)


def conectar_planilha():
    print("Conectando ao Google Planilhas...")
    gc = gspread.service_account(filename=GOOGLE_CREDENTIALS_FILE)
    planilha = gc.open(SPREADSHEET_NAME).sheet1
    print(f"Conectado à planilha '{SPREADSHEET_NAME}'!")
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


def registrar_movimentacao(planilha, dados):
    data_original = dados.get("data", datetime.today().strftime("%d/%m/%Y"))

    if "2023" in data_original or "2024" in data_original or "2025" in data_original:
        dia_mes = data_original[:6]
        data_original = f"{dia_mes}2026"

    tipo = normalizar_tipo(dados.get("tipo", "gasto"))

    raw_valor = dados.get("valor_total", 0)
    print(f"💰 5. Valor bruto recebido da IA: {raw_valor} (Tipo: {type(raw_valor)})")
    valor_total = float(raw_valor)
    if valor_total <= 0:
        raise ValueError("valor_total deve ser maior que zero")

    descricao_original = texto_seguro_planilha(dados.get("descricao", ""))
    total_parcelas = int(dados.get("parcelas", 1))
    if total_parcelas < 1 or total_parcelas > MAX_PARCELAS:
        raise ValueError(f"parcelas deve estar entre 1 e {MAX_PARCELAS}")
    categoria = normalizar_categoria(dados.get("categoria", "Outros"))

    valor_parcela = valor_total / total_parcelas
    valor_formatado = str(round(valor_parcela, 2)).replace(".", ",")

    print(f"🚀 6. Preparando para salvar {total_parcelas} parcela(s)...")
    linha_insercao = 2

    for i in range(total_parcelas):
        data_parcela = calcular_data_parcela(data_original, i)
        descricao_final = (
            f"{descricao_original} (Parcela {i + 1}/{total_parcelas})"
            if total_parcelas > 1
            else descricao_original
        )
        nova_linha = [data_parcela, tipo, valor_formatado, descricao_final, total_parcelas, categoria]
        planilha.insert_row(nova_linha, index=linha_insercao)
        linha_insercao += 1
        print(f"✅ Line {i + 1} salva!")

    if total_parcelas > 1:
        return f"✅ Registado!\nCompra de R$ {valor_total:.2f} ({categoria}) dividida em {total_parcelas}x lançada na planilha."
    return f"✅ Registado!\nAdicionado: {descricao_original} ({categoria}) - R$ {valor_total:.2f}."


def consultar_gastos_mes(planilha, mes_alvo, ano_alvo):
    print(f"🔍 5. Buscando gastos para o período: {mes_alvo}/{ano_alvo}")

    todas_as_linhas = planilha.get_all_values()[1:]
    print(f"📂 6. Total de linhas lidas na planilha: {len(todas_as_linhas)}")

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
