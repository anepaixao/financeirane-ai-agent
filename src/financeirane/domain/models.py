from dataclasses import dataclass


@dataclass
class RegistroFinanceiro:
    data: str
    tipo: str
    valor_total: float
    descricao: str
    parcelas: int
    categoria: str
