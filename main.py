import calendar
import json
import os
from datetime import datetime

import gspread
import telebot
from dotenv import load_dotenv
from google import genai
from google.genai import types


# ==========================================
# 1. CARREGANDO CONFIGURAÇÕES E CHAVES
# ==========================================
load_dotenv()
TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")

if not TOKEN:
    raise RuntimeError("TELEGRAM_TOKEN não encontrado no arquivo .env")

if not GEMINI_KEY:
    raise RuntimeError("GEMINI_API_KEY não encontrado no arquivo .env")


# ==========================================
# 2. CONECTANDO COM O GOOGLE PLANILHAS
# ==========================================
print("Conectando ao Google Planilhas...")
gc = gspread.service_account(filename="credenciais.json")
planilha = gc.open("Financeirane").sheet1
print("Conectado à planilha 'Financeirane'!")


# ==========================================
# 3. CONFIGURANDO A INTELIGÊNCIA (GEMINI)
# ==========================================
client = genai.Client(api_key=GEMINI_KEY)

icategorias_permitidas = ["Cartão de Crédito", "Aluguel", "Feira", "Internet", "Transporte", "Lazer", "Saúde", "Educação", "Outros"]

instrucoes = f"""
Você é a Financeirane, uma assistente financeira pessoal exclusiva da utilizadora. 
A data de hoje é {datetime.today().strftime("%d/%m/%Y")}. O ano é 2026.

As categorias permitidas para os gastos são estritamente estas: {categorias_permitidas}. Use a sua inteligência para classificar o gasto na categoria mais adequada da vida pessoal dela. Se não se encaixar em nenhuma, use "Outros". Se for uma receita/ganho, use "Outros".

Analise a mensagem e retorne ESTRITAMENTE um objeto JSON com o seguinte formato:

Se for para REGISTRAR um gasto ou receita:
{{
  "intencao": "registrar",
  "data": "DD/MM/AAAA",
  "tipo": "gasto" ou "receita",
  "valor_total": número real,
  "descricao": "resumo do gasto",
  "parcelas": número inteiro,
  "categoria": "uma das categorias da lista"
}}

Se for para CONSULTAR ou perguntar quanto tem para pagar/gasto:
{{
  "intencao": "consultar",
  "mes": "MM",
  "ano": "AAAA"
}}
"""


def calcular_data_parcela(data_original, meses_a_adicionar):
    data_base = datetime.strptime(data_original, "%d/%m/%Y")
    mes = data_base.month + meses_a_adicionar
    ano = data_base.year + (mes - 1) // 12
    mes = (mes - 1) % 12 + 1
    ultimo_dia = calendar.monthrange(ano, mes)[1]
    dia = min(data_base.day, ultimo_dia)
    return datetime(ano, mes, dia).strftime("%d/%m/%Y")


# ==========================================
# 4. CONFIGURANDO O BOT DO TELEGRAM
# ==========================================
bot = telebot.TeleBot(TOKEN)
print("A Financeirane está online e pronta para anotar tudo!")


@bot.message_handler(func=lambda message: True)
def responder_mensagem(message):
    texto = message.text
    chat_id = message.chat.id
    
    bot.send_message(chat_id, "⏳ A processar...")
    
    try:
        print("\n-------------------------------------------")
        print(f"📥 1. Mensagem recebida no Telegram: '{texto}'")
        
        # 1. Pede ao Gemini para extrair os dados
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=texto,
            config=types.GenerateContentConfig(
                system_instruction=instrucoes,
                response_mime_type="application/json",
            )
        )
        
        print(f"🧠 2. Resposta bruta da IA:\n{response.text}")
        
        dados = json.loads(response.text)
        print(f"📦 3. JSON transformado em Dicionário: {dados}")
        
        intencao = dados.get('intencao')
        print(f"🎯 4. Intenção detetada: {intencao}")
        
        # ==========================================
        # FLUXO A: REGISTRAR GASTO
        # ==========================================
        if intencao == "registrar":
            data_original = dados.get('data', datetime.today().strftime("%d/%m/%Y"))
            
            if "2023" in data_original or "2024" in data_original or "2025" in data_original:
                dia_mes = data_original[:6]
                data_original = f"{dia_mes}2026"
                
            tipo = dados.get('tipo', 'gasto')
            
            # Tratamento preventivo para erro de conversão de valor
            raw_valor = dados.get('valor_total', 0)
            print(f"💰 5. Valor bruto recebido da IA: {raw_valor} (Tipo: {type(raw_valor)})")
            valor_total = float(raw_valor)
            
            descricao_original = dados.get('descricao', '')
            total_parcelas = int(dados.get('parcelas', 1))
            categoria = dados.get('categoria', 'Outros')
            
            valor_parcela = valor_total / total_parcelas
            valor_formatado = str(round(valor_parcela, 2)).replace('.', ',')
            
            print(f"🚀 6. Preparando para salvar {total_parcelas} parcela(s)...")
            # Variável auxiliar para as parcelas entrarem na ordem correta
            linha_insercao = 2 

            for i in range(total_parcelas):
                data_parcela = calcular_data_parcela(data_original, i)
                descricao_final = f"{descricao_original} (Parcela {i+1}/{total_parcelas})" if total_parcelas > 1 else descricao_original
                
                # Agora inclui a categoria no final (Coluna F)
                nova_linha = [data_parcela, tipo, valor_formatado, descricao_final, total_parcelas, categoria]
                
                # Em vez de append_row (ir pro final), insere forçadamente na linha de inserção
                planilha.insert_row(nova_linha, index=linha_insercao)
                
                # Para as próximas parcelas da mesma compra ficarem abaixo da primeira (Linha 3, Linha 4...)
                linha_insercao += 1
                print(f"✅ Line {i+1} salva!")
                
            if total_parcelas > 1:
                resposta = f"✅ Registado!\nCompra de R$ {valor_total:.2f} ({categoria}) dividida em {total_parcelas}x lançada na planilha."
            else:
                resposta = f"✅ Registado!\nAdicionado: {descricao_original} ({categoria}) - R$ {valor_total:.2f}."
            bot.send_message(chat_id, resposta)
            print("🏁 Fluxo de registro concluído com sucesso!")
            
        # ==========================================
        # FLUXO B: CONSULTAR GASTOS DO MÊS
        # ==========================================
        elif intencao == "consultar":
            mes_alvo = dados.get('mes')
            ano_alvo = dados.get('ano')
            print(f"🔍 5. Buscando gastos para o período: {mes_alvo}/{ano_alvo}")
            
            todas_as_linhas = planilha.get_all_values()[1:]
            print(f"📂 6. Total de linhas lidas na planilha: {len(todas_as_linhas)}")
            
            total_gastos = 0.0
            detalhes_gastos = []
            
            for linha in todas_as_linhas:
                if len(linha) < 4:
                    continue
                    
                data_linha = linha[0]
                tipo_linha = linha[1]
                valor_linha = linha[2]
                desc_linha = linha[3]
                cat_linha = linha[5] if len(linha) >= 6 else "Outros"
                
                try:
                    data_dt = datetime.strptime(data_linha, "%d/%m/%Y")
                    if f"{data_dt.month:02d}" == mes_alvo and f"{data_dt.year}" == ano_alvo:
                        if tipo_linha == "gasto":
                            valor_num = float(valor_linha.replace(',', '.'))
                            total_gastos += valor_num
                            detalhes_gastos.append(f"• [{cat_linha}] {desc_linha}: R$ {valor_num:.2f}")
                except:
                    continue
            
            if total_gastos > 0:
                resposta_consulta = f"📊 *Resumo de Contas ({mes_alvo}/{ano_alvo})*\n\n"
                resposta_consulta += "\n".join(detalhes_gastos)
                resposta_consulta += f"\n\n💰 *Total a pagar neste mês: R$ {total_gastos:.2f}*"
            else:
                resposta_consulta = f"🔍 Não encontrei nenhum gasto registado para o mês {mes_alvo}/{ano_alvo}."
                
            bot.send_message(chat_id, resposta_consulta, parse_mode="Markdown")
            print("🏁 Fluxo de consulta concluído com sucesso!")
            
    except Exception as e:
        bot.send_message(chat_id, "Ops, ocorreu um erro ao processar o seu pedido.")
        print(f"❌ ERRO DETALHADO NO TERMINAL: {e}")
        print("-------------------------------------------")


bot.infinity_polling()
