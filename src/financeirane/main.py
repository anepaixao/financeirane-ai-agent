from financeirane.interfaces.telegram_bot import criar_bot, registrar_handlers
from financeirane.logging_config import configurar_logging

__all__ = ["configurar_logging", "criar_bot", "main", "registrar_handlers"]


def main():
    configurar_logging()
    bot = criar_bot()
    bot.infinity_polling()
