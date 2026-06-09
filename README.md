# Financeirane

Assistente financeira autonoma baseada em mensageria, criada para registrar e consultar gastos pessoais a partir de mensagens em texto livre no Telegram.

## Visao Geral

A Financeirane recebe mensagens naturais como `gastei 50 no ifood` ou `comprei um curso de 300 em 3 vezes`, interpreta a intencao com IA, estrutura os dados em JSON e salva as informacoes em uma planilha do Google Sheets.

O sistema tambem entende consultas, como `quanto eu gastei este mes?`, acessa a planilha, filtra os registros do periodo solicitado e devolve um resumo financeiro diretamente no Telegram.

## Stack

- **Linguagem:** Python 3
- **Interface:** Telegram, via `pyTelegramBotAPI` / `telebot`
- **IA / NLP:** Google Gemini 2.5 Flash, via `google-genai`
- **Banco de dados:** Google Sheets, via `gspread` e Google Cloud API
- **Seguranca:** `python-dotenv` para carregar tokens e chaves a partir de `.env`

## Funcionalidades

### Processamento de texto livre

Nao e necessario usar comandos rigidos como `/gasto 50`. A Financeirane interpreta frases naturais e envia o texto para o Gemini, que retorna um JSON padronizado com intencao, data, tipo, valor, descricao, parcelas e categoria.

Exemplo:

```text
gastei 50 no ifood
```

Resultado esperado:

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

### Classificacao automatica de categorias

O bot classifica os registros em uma lista restrita de categorias:

- Cartao de Credito
- Aluguel
- Feira
- Internet
- Transporte
- Lazer
- Saude
- Educacao
- Outros

### Parcelamento automatico

Quando uma compra e informada com parcelas, o codigo calcula automaticamente os vencimentos dos meses seguintes e cria uma linha para cada parcela na planilha.

Exemplo:

```text
comprei um celular de 1200 em 3 vezes
```

O sistema registra:

- Parcela 1/3
- Parcela 2/3
- Parcela 3/3

A logica considera viradas de ano e meses com 28, 30 ou 31 dias.

### Insercao otimizada na planilha

Os registros sao inseridos sempre na linha 2 do Google Sheets, logo abaixo do cabecalho. Assim, os lancamentos mais recentes aparecem primeiro quando a planilha e aberta.

### Consultas e relatorios

A IA diferencia mensagens de registro e mensagens de consulta. Em perguntas como:

```text
quanto eu gastei este mes?
```

o bot acessa o Google Sheets, le todas as linhas, filtra os gastos do mes e ano solicitados, soma os valores e envia um relatorio formatado no Telegram.

## Estrutura do Projeto

```text
.
├── main.py           # Bot principal: Telegram, Gemini, Google Sheets e regras de negocio
├── teste_gemini.py   # Script auxiliar para listar modelos Gemini disponiveis
├── requirements.txt  # Dependencias do ambiente Python
├── .gitignore        # Arquivos sensiveis e locais ignorados pelo Git
└── LICENSE           # Licenca MIT
```

## Configuracao

### 1. Criar e ativar o ambiente virtual

```bash
python3 -m venv venv
source venv/bin/activate
```

### 2. Instalar as dependencias

```bash
pip install -r requirements.txt
```

Dependencias principais esperadas pelo projeto:

```bash
pip install pyTelegramBotAPI google-genai google-generativeai gspread python-dotenv
```

### 3. Criar o arquivo `.env`

Na raiz do projeto, crie um arquivo `.env` com:

```env
TELEGRAM_TOKEN=seu_token_do_telegram
GEMINI_API_KEY=sua_chave_do_gemini
```

### 4. Configurar credenciais do Google Sheets

1. Crie um projeto no Google Cloud.
2. Ative a Google Sheets API.
3. Crie uma conta de servico.
4. Baixe o arquivo JSON de credenciais.
5. Renomeie o arquivo para `credenciais.json`.
6. Coloque o arquivo na raiz do projeto.
7. Compartilhe a planilha `Financeirane` com o e-mail da conta de servico.

O arquivo `credenciais.json` esta no `.gitignore` e nao deve ser versionado.

### 5. Preparar a planilha

Crie uma planilha no Google Sheets chamada:

```text
Financeirane
```

Use a primeira aba da planilha com este cabecalho:

```text
Data | Tipo | Valor | Descricao | Parcelas | Categoria
```

## Como Executar

Com o ambiente virtual ativo:

```bash
python main.py
```

Se tudo estiver configurado corretamente, o terminal exibira mensagens indicando que a conexao com o Google Sheets foi realizada e que a Financeirane esta online.

## Testar Modelos Gemini

Para listar os modelos disponiveis para a sua chave:

```bash
python teste_gemini.py
```

## Exemplos de Uso

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

Consultar gastos:

```text
quanto eu tenho para pagar este mes?
```

## Seguranca

Nunca envie para o GitHub:

- `.env`
- `credenciais.json`
- tokens do Telegram
- chaves da API Gemini
- credenciais do Google Cloud

Esses arquivos ja estao previstos no `.gitignore`.

## Licenca

Este projeto esta licenciado sob a licenca MIT.
