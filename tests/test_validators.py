import os

import pytest

os.environ.setdefault("TELEGRAM_TOKEN", "telegram-token-ficticio")
os.environ.setdefault("GEMINI_API_KEY", "gemini-api-key-ficticia")
os.environ.setdefault("AUTHORIZED_CHAT_IDS", "123456789")

from config import CATEGORIAS_PERMITIDAS, MAX_PARCELAS, TIPOS_PERMITIDOS
from exceptions import EntradaInvalidaError
from models import RegistroFinanceiro
from validators import (
    MAX_DESCRICAO,
    validar_categoria,
    validar_data,
    validar_descricao,
    validar_parcelas,
    validar_registro,
    validar_tipo,
    validar_valor,
)


def criar_registro_valido(**overrides):
    dados = {
        "data": "24/07/2026",
        "tipo": "gasto",
        "valor_total": 100.0,
        "descricao": "Mercado",
        "parcelas": 1,
        "categoria": "Outros",
    }
    dados.update(overrides)
    return RegistroFinanceiro(**dados)


def test_validar_data_aceita_data_valida():
    assert validar_data("24/07/2026") is None


@pytest.mark.parametrize("data", ["31/02/2026", "2026-07-24", None])
def test_validar_data_rejeita_valores_invalidos(data):
    with pytest.raises(EntradaInvalidaError):
        validar_data(data)


@pytest.mark.parametrize("valor", [1, 10.5, "99.90"])
def test_validar_valor_aceita_valores_positivos(valor):
    assert validar_valor(valor) is None


@pytest.mark.parametrize("valor", [0, -1, "abc", None])
def test_validar_valor_rejeita_valores_invalidos(valor):
    with pytest.raises(EntradaInvalidaError):
        validar_valor(valor)


@pytest.mark.parametrize("tipo", sorted(TIPOS_PERMITIDOS))
def test_validar_tipo_aceita_tipos_permitidos(tipo):
    assert validar_tipo(tipo) is None


def test_validar_tipo_rejeita_tipo_desconhecido():
    with pytest.raises(EntradaInvalidaError):
        validar_tipo("investimento")


@pytest.mark.parametrize("categoria", CATEGORIAS_PERMITIDAS)
def test_validar_categoria_aceita_categorias_permitidas(categoria):
    assert validar_categoria(categoria) is None


def test_validar_categoria_rejeita_categoria_desconhecida():
    with pytest.raises(EntradaInvalidaError):
        validar_categoria("Categoria Inexistente")


@pytest.mark.parametrize("parcelas", [1, MAX_PARCELAS])
def test_validar_parcelas_aceita_limites_validos(parcelas):
    assert validar_parcelas(parcelas) is None


@pytest.mark.parametrize("parcelas", [0, -1, MAX_PARCELAS + 1, 1.5, "2"])
def test_validar_parcelas_rejeita_valores_invalidos(parcelas):
    with pytest.raises(EntradaInvalidaError):
        validar_parcelas(parcelas)


@pytest.mark.parametrize("parcelas", [True, False])
def test_validar_parcelas_documenta_comportamento_de_bool(parcelas):
    # bool e subtipo de int em Python; a implementacao atual aceita True como 1
    # e rejeita False por equivaler a 0.
    if parcelas:
        assert validar_parcelas(parcelas) is None
    else:
        with pytest.raises(EntradaInvalidaError):
            validar_parcelas(parcelas)


@pytest.mark.parametrize("descricao", ["Mercado", "  Mercado  "])
def test_validar_descricao_aceita_texto_valido(descricao):
    assert validar_descricao(descricao) is None


@pytest.mark.parametrize("descricao", ["", "   ", 123])
def test_validar_descricao_rejeita_valores_invalidos(descricao):
    with pytest.raises(EntradaInvalidaError):
        validar_descricao(descricao)


def test_validar_descricao_rejeita_texto_acima_do_limite():
    with pytest.raises(EntradaInvalidaError):
        validar_descricao("a" * (MAX_DESCRICAO + 1))


def test_validar_registro_retorna_o_proprio_registro_quando_valido():
    registro = criar_registro_valido()

    assert validar_registro(registro) is registro


def test_validar_registro_rejeita_objeto_que_nao_seja_registro_financeiro():
    with pytest.raises(EntradaInvalidaError):
        validar_registro({"data": "24/07/2026"})


def test_validar_registro_propaga_entrada_invalida_quando_campo_invalido():
    registro = criar_registro_valido(valor_total=0)

    with pytest.raises(EntradaInvalidaError):
        validar_registro(registro)
