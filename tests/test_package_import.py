import financeirane
from exceptions import InterpretacaoIAError as InterpretacaoIAErrorCompat
from financeirane.domain.exceptions import InterpretacaoIAError
from financeirane.domain.models import RegistroFinanceiro
from financeirane.domain.validators import validar_registro
from models import RegistroFinanceiro as RegistroFinanceiroCompat
from validators import validar_registro as validar_registro_compat


def test_financeirane_package_importavel():
    assert financeirane.__file__ is not None


def test_domain_package_importavel():
    assert RegistroFinanceiro.__name__ == "RegistroFinanceiro"
    assert validar_registro.__name__ == "validar_registro"
    assert InterpretacaoIAError.__name__ == "InterpretacaoIAError"


def test_wrappers_temporarios_preservam_identidade():
    assert RegistroFinanceiroCompat is RegistroFinanceiro
    assert validar_registro_compat is validar_registro
    assert InterpretacaoIAErrorCompat is InterpretacaoIAError
