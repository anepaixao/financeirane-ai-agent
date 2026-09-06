import financeirane
import financeirane.ai_service as package_ai_service
import financeirane.config as package_config
import financeirane.logging_config as package_logging_config
from ai_service import interpretar_mensagem as interpretar_mensagem_compat
from ai_service import montar_system_prompt as montar_system_prompt_compat
from ai_service import validar_resposta_gemini as validar_resposta_gemini_compat
from config import parse_authorized_chat_ids as parse_authorized_chat_ids_compat
from exceptions import InterpretacaoIAError as InterpretacaoIAErrorCompat
from financeirane.domain.exceptions import InterpretacaoIAError
from financeirane.domain.models import RegistroFinanceiro
from financeirane.domain.validators import validar_registro
from logging_config import configurar_logging as configurar_logging_compat
from logging_config import obter_log_level as obter_log_level_compat
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
    assert parse_authorized_chat_ids_compat is package_config.parse_authorized_chat_ids
    assert configurar_logging_compat is package_logging_config.configurar_logging
    assert obter_log_level_compat is package_logging_config.obter_log_level
    assert montar_system_prompt_compat is package_ai_service.montar_system_prompt
    assert validar_resposta_gemini_compat is package_ai_service.validar_resposta_gemini
    assert interpretar_mensagem_compat is package_ai_service.interpretar_mensagem
