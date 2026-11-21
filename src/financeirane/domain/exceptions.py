class FinanceiraneError(Exception):
    pass


class InterpretacaoIAError(FinanceiraneError):
    pass


class IAQuotaExcedidaError(FinanceiraneError):
    pass


class IAIndisponivelError(FinanceiraneError):
    pass


class IAErroInesperado(FinanceiraneError):
    pass


class EntradaInvalidaError(FinanceiraneError):
    pass
