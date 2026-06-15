# 🤖 Financeirane - Autonomous AI Financial Agent

> **Status do Projeto:** Ativo e em operação contínua.  
> Sistema agêntico modular construído em Python, integrando Modelos de Linguagem (LLM), Telegram e Google Workspace APIs.

A **Financeirane** é uma assistente financeira autônoma baseada em mensageria, desenhada para eliminar o atrito do registro de fluxo de caixa pessoal. Operando diretamente via Telegram, ela não exige comandos engessados: interpreta linguagem natural, categoriza dados dinamicamente com **Google Gemini 2.5 Flash** e gerencia um banco de dados em nuvem usando **Google Sheets** em tempo real.

O objetivo do projeto é simples: transformar frases comuns como `gastei 50 no ifood` ou `comprei um curso de 300 em 3 vezes` em registros financeiros organizados, consultáveis e persistidos automaticamente.

---

## 🧠 Arquitetura do Sistema Agêntico

A Financeirane segue um fluxo inspirado em sistemas agênticos: **perceber, raciocinar, agir e iterar**.

### 1. Percepção: Input via Telegram

O bot recebe mensagens naturais pelo Telegram usando `pyTelegramBotAPI`. O acesso é protegido por `AUTHORIZED_CHAT_IDS`, garantindo que apenas chats explicitamente autorizados possam registrar dados ou consultar informações financeiras.

Exemplos de entrada:

```text
gastei 50 no ifood
comprei um celular de 1200 em 3 vezes
quanto eu gastei este mês?
```

### 2. Raciocínio: NLP com Gemini

A API do **Google Gemini 2.5 Flash** atua como motor de interpretação. Ela identifica a intenção da mensagem, extrai valores, datas, descrições, parcelas e categorias, retornando um JSON estruturado para o restante da aplicação.

### 3. Ação: Python + Google Sheets

Com o JSON interpretado, a camada Python executa a regra de negócio: valida dados, calcula parcelas, normaliza categorias, grava linhas na planilha ou consulta registros existentes. O Google Sheets funciona como banco de dados em nuvem, acessado via `gspread` e credenciais do Google Cloud.

### 4. Iteração: Resposta ao Usuário

Após registrar ou consultar os dados, a Financeirane devolve uma resposta formatada no próprio Telegram, fechando o ciclo sem que o usuário precise abrir planilhas ou preencher formulários manualmente.

---

## ⚙️ Stack Tecnológica

- **Linguagem:** Python 3
- **Interface de usuário:** Telegram, via `pyTelegramBotAPI` / `telebot`
- **IA / NLP:** Google Gemini 2.5 Flash, via `google-genai`
- **Banco de dados em nuvem:** Google Sheets, via `gspread`
- **Configuração segura:** `python-dotenv`
- **Credenciais externas:** Google Cloud Service Account

---

## ✨ Funcionalidades em Destaque

### Processamento de Texto Livre para JSON

Não é necessário usar comandos rígidos como `/gasto 50`. A IA interpreta linguagem natural e estrutura a carga de dados.

**Input:**

```text
gastei 50 no ifood
```

**Output do motor de IA:**

```json
{
  "intencao": "registrar",
  "data": "09/06/2026",
  "tipo": "gasto",
  "valor_total": 50,
  "descricao": "ifood",
  "parcelas": 1,
  "categoria": "Lazer"
}
```

### Classificação Automática de Categorias

O sistema classifica os lançamentos em uma lista controlada de categorias pessoais:

- Cartão de Crédito
- Aluguel
- Feira
- Internet
- Transporte
- Lazer
- Saúde
- Educação
- Outros

### Motor de Parcelamento Inteligente

Ao informar uma compra parcelada, como:

```text
comprei um celular de 1200 em 3 vezes
```

A Financeirane calcula os vencimentos futuros, cria uma linha para cada parcela e identifica cada registro como `Parcela 1/3`, `Parcela 2/3`, `Parcela 3/3`.

A lógica considera viradas de mês e de ano, incluindo meses com 28, 30 ou 31 dias.

### Inserção Otimizada no Google Sheets

Os registros são gravados sempre na **linha 2** da planilha, logo abaixo do cabeçalho. Isso mantém os lançamentos mais recentes no topo, facilitando a visualização imediata ao abrir o documento.

### Consultas Bidirecionais

O bot diferencia mensagens de registro e de consulta. Ao perguntar:

```text
quanto eu gastei este mês?
```

A aplicação lê o Google Sheets, filtra os gastos do mês e ano solicitados, soma os valores e devolve um relatório diretamente no Telegram.

### Segurança de Acesso

A variável `AUTHORIZED_CHAT_IDS` restringe quem pode usar o bot. Mesmo que outra pessoa encontre o bot no Telegram, ela não consegue registrar dados nem consultar sua planilha.

---

## 🏗️ Estrutura do Projeto

```text
.
├── main.py             # Maestro: escuta o Telegram e coordena os fluxos
├── config.py           # Carrega variáveis do .env e constantes do projeto
├── gemini_service.py   # Cérebro: envia texto ao Gemini e retorna JSON estruturado
├── sheets_service.py   # Memória: registra e consulta dados no Google Sheets
├── teste_gemini.py     # Script auxiliar para listar modelos Gemini disponíveis
├── requirements.txt    # Dependências do ambiente Python
├── .env.example        # Exemplo seguro das variáveis de ambiente
├── .gitignore          # Arquivos sensíveis e locais ignorados pelo Git
└── LICENSE             # Licença MIT
```

---

## 🚀 Como Configurar e Executar

### 1. Clonar o repositório

```bash
git clone <url-do-repositorio>
cd financeirane-ai-agent
```

Se você já está na pasta do projeto, pule esta etapa.

### 2. Criar e ativar o ambiente virtual

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Instalar as dependências

```bash
pip install -r requirements.txt
```

Dependências principais:

```text
pyTelegramBotAPI
google-genai
google-generativeai
gspread
python-dotenv
```

### 4. Configurar variáveis de ambiente

Crie um arquivo `.env` na raiz do projeto. Você pode usar o `.env.example` como referência.

```env
TELEGRAM_TOKEN=seu_token_do_telegram
GEMINI_API_KEY=sua_chave_do_gemini
AUTHORIZED_CHAT_IDS=123456789
```

Para descobrir o ID do seu chat, inicie o bot e envie:

```text
/id
```

ou:

```text
/meu_id
```

Para autorizar mais de um chat, separe os IDs por vírgula:

```env
AUTHORIZED_CHAT_IDS=123456789,987654321
```

### 5. Configurar credenciais do Google Cloud

1. Crie um projeto no Google Cloud.
2. Ative a **Google Sheets API**.
3. Crie uma **conta de serviço**.
4. Baixe o arquivo JSON de credenciais.
5. Renomeie o arquivo para `credenciais.json`.
6. Coloque o arquivo na raiz do projeto.
7. Compartilhe a planilha `Financeirane` com o e-mail da conta de serviço.

O arquivo `credenciais.json` já está protegido pelo `.gitignore` e não deve ser versionado.

### 6. Preparar a planilha

Crie uma planilha no Google Sheets chamada:

```text
Financeirane
```

Na primeira aba, use o cabeçalho obrigatório:

```text
Data | Tipo | Valor | Descricao | Parcelas | Categoria
```

### 7. Iniciar o bot

Com o ambiente virtual ativo:

```bash
python3 main.py
```

Ou diretamente pelo Python do ambiente virtual:

```bash
venv/bin/python3 main.py
```

Se tudo estiver configurado corretamente, o terminal exibirá mensagens indicando a conexão com o Google Sheets e que a Financeirane está online.

---

## 🧪 Testar Modelos Gemini

Para listar os modelos disponíveis para sua chave Gemini:

```bash
python3 teste_gemini.py
```

---

## 💬 Exemplos de Uso

Registrar gasto simples:

```text
gastei 42 no mercado
```

Registrar compra parcelada:

```text
comprei uma cadeira de 600 reais em 4 vezes
```

Registrar receita:

```text
recebi 1500 de freelas
```

Consultar gastos do mês:

```text
quanto eu tenho para pagar este mês?
```

Consultar um período específico:

```text
quanto gastei em junho de 2026?
```

---

## 🛡️ Segurança e Privacidade

A Financeirane foi pensada para uso pessoal com proteção de acesso e isolamento de credenciais.

Nunca envie para o GitHub:

- `.env`
- `credenciais.json`
- tokens do Telegram
- chaves da API Gemini
- credenciais do Google Cloud

Esses arquivos já estão previstos no `.gitignore`.

Além disso, o bot usa `AUTHORIZED_CHAT_IDS` para impedir que pessoas não autorizadas registrem dados ou consultem sua planilha financeira.

---

## 📌 Roadmap Possível

- Suporte a múltiplas planilhas ou abas por usuário.
- Relatórios por categoria.
- Resumo semanal e mensal automático.
- Gráficos financeiros usando dados do Google Sheets.
- Migração opcional para banco relacional dedicado.
- Deploy contínuo em servidor ou plataforma cloud.

---

## 📄 Licença

Este projeto está licenciado sob a licença MIT.

---

Arquitetado e desenvolvido por **Ane Paixão**.
