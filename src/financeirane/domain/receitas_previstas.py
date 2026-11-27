from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from enum import Enum

from financeirane.domain.exceptions import EntradaInvalidaError


class StatusReceita(str, Enum):
    PREVISTA = "prevista"


@dataclass(frozen=True)
class ReceitaPrevista:
    descricao: str
    valor: Decimal
    data_prevista: date
    status: StatusReceita

    def __post_init__(self):
        if not isinstance(self.descricao, str) or not self.descricao.strip():
            raise EntradaInvalidaError("Descrição da receita não pode ser vazia.")
        object.__setattr__(self, "descricao", self.descricao.strip())

        if isinstance(self.valor, bool) or not isinstance(
            self.valor, (Decimal, int, str)
        ):
            raise EntradaInvalidaError("Valor da receita deve ser monetário.")
        try:
            valor = Decimal(str(self.valor))
            if not valor.is_finite():
                raise EntradaInvalidaError("Valor da receita deve ser finito.")
            valor = valor.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        except (InvalidOperation, ValueError) as exc:
            raise EntradaInvalidaError("Valor da receita deve ser monetário.") from exc
        if valor <= 0:
            raise EntradaInvalidaError("Valor da receita deve ser maior que zero.")
        object.__setattr__(self, "valor", valor)

        if type(self.data_prevista) is not date:
            raise EntradaInvalidaError("Data prevista deve ser uma data válida.")

        try:
            object.__setattr__(self, "status", StatusReceita(self.status))
        except (ValueError, TypeError) as exc:
            raise EntradaInvalidaError("Status da receita inválido.") from exc
