import logging

logger = logging.getLogger(__name__)


def configurar_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )


def registrar_handlers(bot, planilha):
    from ai_service import interpretar_mensagem
    from config import AUTHORIZED_CHAT_IDS, MAX_MESSAGE_LENGTH
    from models import RegistroFinanceiro
    from sheets_service import consultar_gastos_mes, registrar_movimentacao

    @bot.message_handler(func=lambda message: True)
    def responder_mensagem(message):
        texto = message.text
        chat_id = message.chat.id
        user_id = getattr(getattr(message, "from_user", None), "id", None)

        if user_id not in AUTHORIZED_CHAT_IDS:
            logger.warning(
                "Mensagem ignorada de usuário não autorizado. user_id=%s", user_id
            )
            return

        if not texto:
            bot.send_message(chat_id, "Envie uma mensagem de texto para eu processar.")
            return

        if texto in ("/id", "/meu_id"):
            bot.send_message(
                chat_id,
                f"O seu user ID é: `{user_id}`\nO ID deste chat é: `{chat_id}`",
                parse_mode="Markdown",
            )
            return

        if len(texto) > MAX_MESSAGE_LENGTH:
            bot.send_message(
                chat_id, "Mensagem muito longa. Envie um pedido mais curto."
            )
            return

        bot.send_message(chat_id, "⏳ A processar...")

        try:
            logger.info("Mensagem autorizada recebida. tamanho=%s", len(texto))

            dados = interpretar_mensagem(texto)

            intencao = (
                "registrar"
                if isinstance(dados, RegistroFinanceiro)
                else dados.get("intencao")
            )
            logger.info("Intenção detectada pela IA. intencao=%s", intencao)

            if intencao == "registrar":
                resposta = registrar_movimentacao(planilha, dados)
                bot.send_message(chat_id, resposta)
                logger.info("Fluxo de registro concluído com sucesso.")
                return

            if intencao == "consultar":
                resposta = consultar_gastos_mes(
                    planilha, dados.get("mes"), dados.get("ano")
                )
                bot.send_message(chat_id, resposta, parse_mode="Markdown")
                logger.info("Fluxo de consulta concluído com sucesso.")
                return

            bot.send_message(
                chat_id,
                "Não consegui entender se você quer registrar ou consultar uma informação.",
            )

        except Exception:
            bot.send_message(chat_id, "Ops, ocorreu um erro ao processar o seu pedido.")
            logger.exception("Erro ao processar mensagem autorizada.")


def criar_bot():
    import telebot

    from config import TELEGRAM_TOKEN
    from sheets_service import conectar_planilha

    planilha = conectar_planilha()
    bot = telebot.TeleBot(TELEGRAM_TOKEN)
    registrar_handlers(bot, planilha)
    logger.info("A Financeirane está online e pronta para anotar tudo.")
    return bot


def main():
    configurar_logging()
    bot = criar_bot()
    bot.infinity_polling()


if __name__ == "__main__":
    main()
