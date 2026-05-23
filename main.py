import os
import telebot
from dotenv import load_dotenv

# Carrega as variáveis do arquivo .env
load_dotenv()
TOKEN = os.getenv('TELEGRAM_TOKEN')

# Inicializa a Financeirane
bot = telebot.TeleBot(TOKEN)

print("🤖 A Financeirane está online e ouvindo...")

# Evento que escuta todas as mensagens de texto
@bot.message_handler(func=lambda message: True)
def responder_mensagem(message):
    texto = message.text
    chat_id = message.chat.id
    
    print(f"Nova mensagem recebida: {texto}")
    
    # Resposta de teste
    resposta = f"Oi! Eu sou a Financeirane. Você me enviou: \"{texto}\". Em breve vou anotar isso no seu cofrinho!"
    bot.send_message(chat_id, resposta)

# Mantém o bot rodando continuamente
bot.infinity_polling()