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


def criar_compromisso(**alteracoes):
    dados = {
        "descricao": "  Conta de energia  ",
        "valor": Decimal("49.25"),
        "vencimento": date(2026, 11, 30),
        "tipo": TipoCompromisso.CONTA,
        "status": StatusCompromisso.PENDENTE,
    }
    dados.update(alteracoes)
    return CompromissoFinanceiro(**dados)


def test_criar_compromisso_valido_normaliza_descricao_e_valor():
    compromisso = criar_compromisso()

    assert compromisso.descricao == "Conta de energia"
    assert compromisso.valor == Decimal("49.25")
    assert compromisso.valor.as_tuple().exponent == -2
    assert compromisso.vencimento == date(2026, 11, 30)
    assert compromisso.tipo is TipoCompromisso.CONTA
    assert compromisso.status is StatusCompromisso.PENDENTE


@pytest.mark.parametrize("tipo", list(TipoCompromisso))
def test_aceita_todos_os_tipos_permitidos(tipo):
    assert criar_compromisso(tipo=tipo).tipo is tipo


@pytest.mark.parametrize("status", list(StatusCompromisso))
def test_aceita_todos_os_status_permitidos(status):
    assert criar_compromisso(status=status).status is status


def test_aceita_valores_textuais_validos_e_armazena_enums():
    compromisso = criar_compromisso(tipo="assinatura", status="pago")

    assert compromisso.tipo is TipoCompromisso.ASSINATURA
    assert compromisso.status is StatusCompromisso.PAGO


@pytest.mark.parametrize("valor", [0, Decimal("0.004"), -1, Decimal("-0.01")])
def test_rejeita_valor_zero_ou_negativo(valor):
    with pytest.raises(EntradaInvalidaError, match="maior que zero"):
        criar_compromisso(valor=valor)


@pytest.mark.parametrize("valor", [12.5, True, None, "abc", "NaN", "Infinity"])
def test_rejeita_valor_nao_monetario_ou_nao_finito(valor):
    with pytest.raises(EntradaInvalidaError, match="Valor do compromisso"):
        criar_compromisso(valor=valor)


@pytest.mark.parametrize("valor, esperado", [(10, "10.00"), ("33.335", "33.34")])
def test_valor_usa_decimal_e_arredondamento_half_up(valor, esperado):
    assert criar_compromisso(valor=valor).valor == Decimal(esperado)


@pytest.mark.parametrize("descricao", ["", "   ", None, 123])
def test_rejeita_descricao_vazia_ou_invalida(descricao):
    with pytest.raises(EntradaInvalidaError, match="Descrição do compromisso"):
        criar_compromisso(descricao=descricao)


@pytest.mark.parametrize("tipo", ["cartao", "CONTA", None])
def test_rejeita_tipo_invalido(tipo):
    with pytest.raises(EntradaInvalidaError, match="Tipo de compromisso inválido"):
        criar_compromisso(tipo=tipo)


@pytest.mark.parametrize("status", ["vencido", "PAGO", None])
def test_rejeita_status_invalido(status):
    with pytest.raises(EntradaInvalidaError, match="Status de compromisso inválido"):
        criar_compromisso(status=status)


@pytest.mark.parametrize("vencimento", ["30/11/2026", None, datetime(2026, 11, 30)])
def test_rejeita_vencimento_que_nao_seja_date(vencimento):
    with pytest.raises(EntradaInvalidaError, match="Vencimento"):
        criar_compromisso(vencimento=vencimento)


def test_aceita_vencimento_bissexto():
    compromisso = criar_compromisso(vencimento=date(2028, 2, 29))

    assert compromisso.vencimento == date(2028, 2, 29)


def test_marcar_como_pago_cria_novo_compromisso_sem_alterar_original():
    pendente = criar_compromisso()

    pago = pendente.marcar_como_pago()

    assert pago is not pendente
    assert pago.status is StatusCompromisso.PAGO
    assert pendente.status is StatusCompromisso.PENDENTE
    assert pago.descricao == pendente.descricao
    assert pago.valor == pendente.valor
    assert pago.vencimento == pendente.vencimento
    assert pago.tipo is pendente.tipo


def test_marcar_como_pago_repetidamente_retorna_mesma_instancia():
    pago = criar_compromisso(status=StatusCompromisso.PAGO)

    assert pago.marcar_como_pago() is pago
    assert pago.marcar_como_pago().status is StatusCompromisso.PAGO


def test_marcar_como_pendente_cria_novo_compromisso_sem_alterar_original():
    pago = criar_compromisso(status=StatusCompromisso.PAGO)

    pendente = pago.marcar_como_pendente()

    assert pendente is not pago
    assert pendente.status is StatusCompromisso.PENDENTE
    assert pago.status is StatusCompromisso.PAGO
    assert pendente.valor == pago.valor


def test_marcar_como_pendente_repetidamente_retorna_mesma_instancia():
    pendente = criar_compromisso()

    assert pendente.marcar_como_pendente() is pendente


def test_transicoes_de_estado_sao_reversiveis_e_deterministicas():
    inicial = criar_compromisso()

    final = inicial.marcar_como_pago().marcar_como_pendente()

    assert final == inicial
    assert final is not inicial


def test_atualizar_campos_validos_cria_novo_compromisso():
    original = criar_compromisso()

    atualizado = original.atualizar(
        descricao="  Internet  ",
        valor="33.335",
        vencimento=date(2026, 12, 15),
        tipo="assinatura",
    )

    assert atualizado is not original
    assert atualizado.descricao == "Internet"
    assert atualizado.valor == Decimal("33.34")
    assert atualizado.vencimento == date(2026, 12, 15)
    assert atualizado.tipo is TipoCompromisso.ASSINATURA
    assert atualizado.status is StatusCompromisso.PENDENTE
    assert original.valor == Decimal("49.25")
    assert original.descricao == "Conta de energia"


def test_atualizar_sem_alteracoes_retorna_mesma_instancia():
    compromisso = criar_compromisso()

    assert compromisso.atualizar() is compromisso


@pytest.mark.parametrize(
    ("campo", "valor", "mensagem"),
    [
        ("descricao", "   ", "Descrição do compromisso"),
        ("valor", 0, "maior que zero"),
        ("valor", -5, "maior que zero"),
        ("vencimento", "31/02/2026", "Vencimento"),
        ("tipo", "cartao", "Tipo de compromisso"),
        ("status", "pago", "Campo de atualização"),
        ("campo_desconhecido", 1, "Campo de atualização"),
    ],
)
def test_atualizar_rejeita_campos_ou_valores_invalidos(campo, valor, mensagem):
    compromisso = criar_compromisso()

    with pytest.raises(EntradaInvalidaError, match=mensagem):
        compromisso.atualizar(**{campo: valor})

    assert compromisso.status is StatusCompromisso.PENDENTE
    assert compromisso.valor == Decimal("49.25")


def test_compromisso_continua_imutavel():
    compromisso = criar_compromisso()

    with pytest.raises(FrozenInstanceError):
        compromisso.status = StatusCompromisso.PAGO


def test_registro_financeiro_existente_continua_funcionando():
    registro = RegistroFinanceiro(
        data="21/11/2026",
        tipo="gasto",
        valor_total=15.0,
        descricao="Mercado",
        parcelas=1,
        categoria="Alimentação",
        forma_pagamento="Pix",
        conta_cartao="Banco do Brasil",
    )

    assert registro.valor_total == 15.0
    assert registro.parcelas == 1
