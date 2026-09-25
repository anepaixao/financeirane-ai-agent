from financeirane.interfaces.telegram_bot import criar_bot, registrar_handlers
from logging_config import configurar_logging

__all__ = ["criar_bot", "main", "registrar_handlers"]


def main():
    configurar_logging()
    bot = criar_bot()
    bot.infinity_polling()


if __name__ == "__main__":
    main()
