from dataclasses import dataclass, replace
from datetime import date
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from enum import Enum

from financeirane.domain.exceptions import EntradaInvalidaError


class TipoCompromisso(str, Enum):
    CONTA = "conta"
    ASSINATURA = "assinatura"
    PARCELA = "parcela"
    OUTRO = "outro"


class StatusCompromisso(str, Enum):
    PENDENTE = "pendente"
    PAGO = "pago"


@dataclass(frozen=True)
class CompromissoFinanceiro:
    descricao: str
    valor: Decimal
    vencimento: date
    tipo: TipoCompromisso
    status: StatusCompromisso

    def esta_atrasado(self, data_referencia: date) -> bool:
        if type(data_referencia) is not date:
            raise EntradaInvalidaError("Data de referência deve ser uma data válida.")
        return (
            self.status is StatusCompromisso.PENDENTE
            and self.vencimento < data_referencia
        )

    def marcar_como_pago(self):
        if self.status is StatusCompromisso.PAGO:
            return self
        return replace(self, status=StatusCompromisso.PAGO)

    def marcar_como_pendente(self):
        if self.status is StatusCompromisso.PENDENTE:
            return self
        return replace(self, status=StatusCompromisso.PENDENTE)

    def atualizar(self, **alteracoes):
        campos_permitidos = {"descricao", "valor", "vencimento", "tipo"}
        if not set(alteracoes) <= campos_permitidos:
            raise EntradaInvalidaError("Campo de atualização do compromisso inválido.")
        if not alteracoes:
            return self
        return replace(self, **alteracoes)

    def __post_init__(self):
        if not isinstance(self.descricao, str) or not self.descricao.strip():
            raise EntradaInvalidaError("Descrição do compromisso não pode ser vazia.")
        object.__setattr__(self, "descricao", self.descricao.strip())

        if isinstance(self.valor, bool) or not isinstance(
            self.valor, (Decimal, int, str)
        ):
            raise EntradaInvalidaError("Valor do compromisso deve ser monetário.")
        try:
            valor = Decimal(str(self.valor))
            if not valor.is_finite():
                raise EntradaInvalidaError("Valor do compromisso deve ser finito.")
            valor = valor.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        except (InvalidOperation, ValueError) as exc:
            raise EntradaInvalidaError(
                "Valor do compromisso deve ser monetário."
            ) from exc
        if valor <= 0:
            raise EntradaInvalidaError("Valor do compromisso deve ser maior que zero.")
        object.__setattr__(self, "valor", valor)

        if type(self.vencimento) is not date:
            raise EntradaInvalidaError("Vencimento deve ser uma data válida.")

        try:
            object.__setattr__(self, "tipo", TipoCompromisso(self.tipo))
        except ValueError as exc:
            raise EntradaInvalidaError("Tipo de compromisso inválido.") from exc

        try:
            object.__setattr__(self, "status", StatusCompromisso(self.status))
        except ValueError as exc:
            raise EntradaInvalidaError("Status de compromisso inválido.") from exc
