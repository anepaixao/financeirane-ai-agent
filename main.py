import telebot

from config import AUTHORIZED_CHAT_IDS, MAX_MESSAGE_LENGTH, TELEGRAM_TOKEN
from gemini_service import interpretar_mensagem
from sheets_service import conectar_planilha, consultar_gastos_mes, registrar_movimentacao


planilha = conectar_planilha()
bot = telebot.TeleBot(TELEGRAM_TOKEN)
print("A Financeirane está online e pronta para anotar tudo!")


@bot.message_handler(func=lambda message: True)
def responder_mensagem(message):
    texto = message.text
    chat_id = message.chat.id

    if texto in ("/id", "/meu_id"):
        bot.send_message(chat_id, f"O ID deste chat é: `{chat_id}`", parse_mode="Markdown")
        return

    if chat_id not in AUTHORIZED_CHAT_IDS:
        print(f"🚫 Acesso negado para chat_id={chat_id}")
        bot.send_message(
            chat_id,
            "Acesso não autorizado. Envie /id e adicione este ID ao AUTHORIZED_CHAT_IDS no arquivo .env.",
        )
        return

    if not texto:
        bot.send_message(chat_id, "Envie uma mensagem de texto para eu processar.")
        return

    if len(texto) > MAX_MESSAGE_LENGTH:
        bot.send_message(chat_id, "Mensagem muito longa. Envie um pedido mais curto.")
        return

    bot.send_message(chat_id, "⏳ A processar...")

    try:
        print("\n-------------------------------------------")
        print(f"📥 1. Mensagem recebida no Telegram: '{texto}'")

        dados = interpretar_mensagem(texto)
        print(f"📦 3. JSON transformado em Dicionário: {dados}")

        intencao = dados.get("intencao")
        print(f"🎯 4. Intenção detetada: {intencao}")

        if intencao == "registrar":
            resposta = registrar_movimentacao(planilha, dados)
            bot.send_message(chat_id, resposta)
            print("🏁 Fluxo de registro concluído com sucesso!")
            return

        if intencao == "consultar":
            resposta = consultar_gastos_mes(planilha, dados.get("mes"), dados.get("ano"))
            bot.send_message(chat_id, resposta, parse_mode="Markdown")
            print("🏁 Fluxo de consulta concluído com sucesso!")
            return

        bot.send_message(chat_id, "Não consegui entender se você quer registrar ou consultar uma informação.")

    except Exception as e:
        bot.send_message(chat_id, "Ops, ocorreu um erro ao processar o seu pedido.")
        print(f"❌ ERRO DETALHADO NO TERMINAL: {e}")
        print("-------------------------------------------")


if __name__ == "__main__":
    bot.infinity_polling()
