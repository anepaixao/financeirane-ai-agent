from dataclasses import FrozenInstanceError
from datetime import date, datetime
from decimal import Decimal

import pytest

from financeirane.domain.compromissos import (
    CompromissoFinanceiro,
    StatusCompromisso,
    TipoCompromisso,
)
from financeirane.domain.exceptions import EntradaInvalidaError
from financeirane.domain.models import RegistroFinanceiro
from financeirane.domain.receitas_previstas import ReceitaPrevista, StatusReceita


def criar_receita(**alteracoes):
    dados = {
        "descricao": "  Salário  ",
        "valor": Decimal("1700.00"),
        "data_prevista": date(2026, 12, 7),
        "status": StatusReceita.PREVISTA,
    }
    dados.update(alteracoes)
    return ReceitaPrevista(**dados)


def test_criacao_valida_normaliza_descricao_e_preserva_data():
    receita = criar_receita()

    assert receita.descricao == "Salário"
    assert receita.valor == Decimal("1700.00")
    assert receita.valor.as_tuple().exponent == -2
    assert receita.data_prevista == date(2026, 12, 7)
    assert receita.status is StatusReceita.PREVISTA


@pytest.mark.parametrize("status", [StatusReceita.PREVISTA, "prevista"])
def test_aceita_estado_prevista(status):
    assert criar_receita(status=status).status is StatusReceita.PREVISTA


@pytest.mark.parametrize(
    ("valor", "esperado"),
    [(10, "10.00"), ("33.335", "33.34"), (Decimal("0.005"), "0.01")],
)
def test_converte_e_arredonda_valor_com_half_up(valor, esperado):
    receita = criar_receita(valor=valor)

    assert receita.valor == Decimal(esperado)
    assert receita.valor.as_tuple().exponent == -2


@pytest.mark.parametrize("valor", [0, -1, Decimal("-0.01"), Decimal("0.004")])
def test_rejeita_valor_zero_ou_negativo(valor):
    with pytest.raises(EntradaInvalidaError, match="maior que zero"):
        criar_receita(valor=valor)


@pytest.mark.parametrize(
    "valor", [True, False, 12.5, None, "abc", "NaN", "Infinity", Decimal("-Infinity")]
)
def test_rejeita_valor_invalido_ou_nao_finito(valor):
    with pytest.raises(EntradaInvalidaError, match="Valor da receita"):
        criar_receita(valor=valor)


@pytest.mark.parametrize("descricao", ["", "   ", None, 123])
def test_rejeita_descricao_vazia_ou_invalida(descricao):
    with pytest.raises(EntradaInvalidaError, match="Descrição da receita"):
        criar_receita(descricao=descricao)


@pytest.mark.parametrize("data_prevista", [None, "07/12/2026", datetime(2026, 12, 7)])
def test_rejeita_data_que_nao_seja_date_puro(data_prevista):
    with pytest.raises(EntradaInvalidaError, match="Data prevista"):
        criar_receita(data_prevista=data_prevista)


def test_aceita_data_bissexta_valida():
    assert criar_receita(data_prevista=date(2028, 2, 29)).data_prevista == date(
        2028, 2, 29
    )


@pytest.mark.parametrize("status", ["recebida", "PREVISTA", None, []])
def test_rejeita_estado_desconhecido(status):
    with pytest.raises(EntradaInvalidaError, match="Status da receita"):
        criar_receita(status=status)


def test_receita_prevista_e_imutavel():
    receita = criar_receita()

    with pytest.raises(FrozenInstanceError):
        receita.status = "recebida"
    assert receita.status is StatusReceita.PREVISTA


def test_modelos_existentes_continuam_independentes():
    compromisso = CompromissoFinanceiro(
        descricao="Conta de energia",
        valor=Decimal("49.25"),
        vencimento=date(2026, 12, 10),
        tipo=TipoCompromisso.CONTA,
        status=StatusCompromisso.PENDENTE,
    )
    registro = RegistroFinanceiro(
        data="07/12/2026",
        tipo="receita",
        valor_total=1700.0,
        descricao="Salário recebido",
        parcelas=1,
        categoria="Outros",
        forma_pagamento="Pix",
        conta_cartao="Banco do Brasil",
    )

    assert compromisso.status is StatusCompromisso.PENDENTE
    assert registro.tipo == "receita"
    assert criar_receita().status is StatusReceita.PREVISTA
