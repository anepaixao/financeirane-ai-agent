# Compatibilidade temporária durante a migração incremental para src layout.
from financeirane.ai_service import (
    CHAVES_CONSULTA,
    CHAVES_REGISTRO,
    client,
    interpretar_mensagem,
    montar_system_prompt,
    validar_resposta_gemini,
)

__all__ = [
    "CHAVES_CONSULTA",
    "CHAVES_REGISTRO",
    "client",
    "interpretar_mensagem",
    "montar_system_prompt",
    "validar_resposta_gemini",
]
