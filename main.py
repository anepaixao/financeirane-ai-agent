import os
import json
import telebot
import gspread
from google import genai
from google.genai import types
from dotenv import load_dotenv

# ==========================================
# 1. CARREGANDO CONFIGURAÇÕES E CHAVES
# ==========================================
load_dotenv()
TOKEN = os.getenv('TELEGRAM_TOKEN')
GEMINI_KEY = os.getenv('GEMINI_API_KEY')

# ==========================================
# 2. CONECTANDO COM O GOOGLE PLANILHAS
# ==========================================
print("Conectando ao Google Planilhas...")
# Lê o arquivo de credenciais que você baixou
gc = gspread.service_account(filename='credenciais.json')
# Abre a sua planilha pelo nome exato (tem que ser igual está no Drive)
planilha = gc.open('Financeirane').sheet1 
print("Conectado à planilha 'Financeirane'!")

# ==========================================
# 3. CONFIGURANDO A INTELIGÊNCIA (GEMINI)
# ==========================================
client = genai.Client(api_key=GEMINI_KEY)

instrucoes = """
Você é a Financeirane, uma assistente financeira pessoal. 
O usuário vai te enviar mensagens relatando gastos ou receitas.
Extraia os dados e retorne ESTRITAMENTE um objeto JSON válido com as chaves:
- "data": "DD/MM/AAAA" (use a data de hoje ou a data que o usuário informar)
- "tipo": "gasto" ou "receita"
- "valor": numero real (apenas numeros e ponto, sem cifrão)
- "descricao": o que foi comprado ou recebido, de forma resumida
- "parcelas": numero inteiro (se nao especificado, use 1)
"""

# ==========================================
# 4. CONFIGURANDO O BOT DO TELEGRAM
# ==========================================
bot = telebot.TeleBot(TOKEN)
print("A Financeirane está online e pronta para anotar tudo!")

@bot.message_handler(func=lambda message: True)
def responder_mensagem(message):
    texto = message.text
    chat_id = message.chat.id
    
    bot.send_message(chat_id, "⏳ Anotando no seu cofrinho...")
    
    try:
        # 1. Pede para o Gemini extrair os dados
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=texto,
            config=types.GenerateContentConfig(
                system_instruction=instrucoes,
                response_mime_type="application/json",
            )
        )
        
        # 2. Converte o texto JSON que o Gemini devolveu em um dicionário Python
        dados = json.loads(response.text)
        
        # 3. Prepara a linha para escrever na planilha
        # A ordem aqui tem que ser igual ao cabeçalho da sua planilha (A, B, C, D, E)
        nova_linha = [
            dados.get('data', ''),
            dados.get('tipo', ''),
            str(dados.get('valor', '')).replace('.', ','), # Troca ponto por vírgula para o Sheets entender como dinheiro
            dados.get('descricao', ''),
            dados.get('parcelas', 1)
        ]
        
        # 4. Escreve na planilha!
        planilha.append_row(nova_linha)
        
        # 5. Avisa você que deu tudo certo
        mensagem_sucesso = f"Sucesso!\nRegistrei: {dados.get('descricao')} - R$ {dados.get('valor')} na sua planilha."
        bot.send_message(chat_id, mensagem_sucesso)
        
    except Exception as e:
        bot.send_message(chat_id, "Ops, tive um problema ao salvar na planilha.")
        print(f"Erro detalhado: {e}")

bot.infinity_polling()