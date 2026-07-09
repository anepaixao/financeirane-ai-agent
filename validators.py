from datetime import datetime

from config import CATEGORIAS_PERMITIDAS, MAX_PARCELAS, TIPOS_PERMITIDOS
from exceptions import EntradaInvalidaError
from models import RegistroFinanceiro

FORMATO_DATA = "%d/%m/%Y"
MAX_DESCRICAO = 200


def validar_data(data):
    try:
        datetime.strptime(data, FORMATO_DATA)
    except (TypeError, ValueError) as exc:
        raise EntradaInvalidaError("Data inválida. Use o formato DD/MM/AAAA.") from exc


def validar_valor(valor):
    try:
        valor_numero = float(valor)
    except (TypeError, ValueError) as exc:
        raise EntradaInvalidaError("Valor total deve ser numérico.") from exc

    if valor_numero <= 0:
        raise EntradaInvalidaError("Valor total deve ser maior que zero.")


def validar_tipo(tipo):
    if tipo not in TIPOS_PERMITIDOS:
        tipos = ", ".join(sorted(TIPOS_PERMITIDOS))
        raise EntradaInvalidaError(f"Tipo inválido. Use um destes valores: {tipos}.")


def validar_categoria(categoria):
    if categoria not in CATEGORIAS_PERMITIDAS:
        raise EntradaInvalidaError("Categoria inválida. Use uma categoria permitida.")


def validar_parcelas(parcelas):
    if not isinstance(parcelas, int):
        raise EntradaInvalidaError("Parcelas deve ser um número inteiro.")

    if parcelas < 1:
        raise EntradaInvalidaError("Parcelas deve ser maior ou igual a 1.")

    if parcelas > MAX_PARCELAS:
        raise EntradaInvalidaError(f"Parcelas deve ser menor ou igual a {MAX_PARCELAS}.")


def validar_descricao(descricao):
    if not isinstance(descricao, str):
        raise EntradaInvalidaError("Descrição deve ser um texto.")

    descricao_limpa = descricao.strip()
    if not descricao_limpa:
        raise EntradaInvalidaError("Descrição não pode ser vazia.")

    if len(descricao_limpa) > MAX_DESCRICAO:
        raise EntradaInvalidaError(f"Descrição deve ter no máximo {MAX_DESCRICAO} caracteres.")


def validar_registro(registro: RegistroFinanceiro):
    if not isinstance(registro, RegistroFinanceiro):
        raise EntradaInvalidaError("Registro financeiro inválido.")

    validar_data(registro.data)
    validar_valor(registro.valor_total)
    validar_tipo(registro.tipo)
    validar_categoria(registro.categoria)
    validar_parcelas(registro.parcelas)
    validar_descricao(registro.descricao)

    return registro
