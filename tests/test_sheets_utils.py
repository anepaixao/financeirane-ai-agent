import os
from decimal import Decimal

import pytest

os.environ.setdefault("TELEGRAM_TOKEN", "telegram-token-ficticio")
os.environ.setdefault("GEMINI_API_KEY", "gemini-api-key-ficticia")
os.environ.setdefault("AUTHORIZED_CHAT_IDS", "123456789")

from config import CATEGORIAS_PERMITIDAS, TIPOS_PERMITIDOS
from sheets_service import (
    calcular_data_parcela,
    formatar_centavos,
    normalizar_categoria,
    normalizar_tipo,
    texto_seguro_planilha,
    valor_em_centavos,
)


def test_calcular_data_parcela_mantem_dia_em_meses_compativeis():
    assert calcular_data_parcela("15/01/2026", 1) == "15/02/2026"


def test_calcular_data_parcela_ajusta_31_de_janeiro_para_ultimo_dia_de_fevereiro():
    assert calcular_data_parcela("31/01/2026", 1) == "28/02/2026"


def test_calcular_data_parcela_considera_fevereiro_de_ano_bissexto():
    assert calcular_data_parcela("31/01/2024", 1) == "29/02/2024"


def test_calcular_data_parcela_atravessa_mudanca_de_ano():
    assert calcular_data_parcela("30/11/2026", 2) == "30/01/2027"


def test_calcular_data_parcela_preserva_anos_antigos():
    assert calcular_data_parcela("15/07/2025", 0) == "15/07/2025"


def test_texto_seguro_planilha_remove_espacos_externos():
    assert texto_seguro_planilha("  mercado  ") == "mercado"


def test_texto_seguro_planilha_substitui_quebras_de_linha_por_espaco():
    assert texto_seguro_planilha("linha 1\nlinha 2") == "linha 1 linha 2"


@pytest.mark.parametrize("texto", ["=SOMA(A1:A2)", "+10", "-10", "@usuario"])
def test_texto_seguro_planilha_protege_prefixos_de_formula(texto):
    assert texto_seguro_planilha(texto) == f"'{texto}"


def test_texto_seguro_planilha_converte_none_em_string_vazia():
    assert texto_seguro_planilha(None) == ""


def test_texto_seguro_planilha_nao_altera_texto_comum():
    assert texto_seguro_planilha("mercado") == "mercado"


@pytest.mark.parametrize(
    ("valor", "esperado"),
    [
        (100, 10000),
        (33.335, 3334),
        (0.005, 1),
        (10, 1000),
        (10.5, 1050),
        ("10.25", 1025),
        (Decimal("10.25"), 1025),
    ],
)
def test_valor_em_centavos_converte_valores_validos(valor, esperado):
    assert valor_em_centavos(valor) == esperado


@pytest.mark.parametrize(
    ("valor_centavos", "esperado"),
    [
        (10000, "100,00"),
        (3334, "33,34"),
        (1, "0,01"),
        (0, "0,00"),
    ],
)
def test_formatar_centavos(valor_centavos, esperado):
    assert formatar_centavos(valor_centavos) == esperado


@pytest.mark.parametrize("categoria", CATEGORIAS_PERMITIDAS)
def test_normalizar_categoria_preserva_categorias_permitidas(categoria):
    assert normalizar_categoria(categoria) == categoria


def test_normalizar_categoria_retorna_outros_para_categoria_invalida():
    assert normalizar_categoria("Categoria Inexistente") == "Outros"


@pytest.mark.parametrize("tipo", sorted(TIPOS_PERMITIDOS))
def test_normalizar_tipo_preserva_tipos_permitidos(tipo):
    assert normalizar_tipo(tipo) == tipo


def test_normalizar_tipo_normaliza_maiusculas_e_espacos():
    assert normalizar_tipo("  GASTO  ") == "gasto"


@pytest.mark.parametrize("tipo", ["investimento", None])
def test_normalizar_tipo_retorna_gasto_para_valor_invalido_ou_none(tipo):
    assert normalizar_tipo(tipo) == "gasto"
