# Financeirane AI Agent

Financeirane AI Agent é um bot financeiro pessoal para Telegram. Ele interpreta mensagens em linguagem natural com Gemini, valida os dados no domínio da aplicação e registra ou consulta movimentações em uma planilha do Google Sheets.

O sistema serve para registro e consulta de movimentações financeiras pessoais. Ele não fornece aconselhamento financeiro, recomendação de investimento, análise patrimonial ou orientação profissional.

## Problema

Registrar gastos manualmente em planilhas é trabalhoso e fácil de esquecer. A Financeirane reduz esse atrito: a pessoa envia uma frase comum pelo Telegram e o agente transforma a mensagem em um registro estruturado, validado e persistido.

## Funcionalidades

- Registro de gastos e receitas por mensagem de texto.
- Consulta de gastos por mês e ano.
- Interpretação de linguagem natural com Gemini.
- Classificação em categorias permitidas.
- Validação de dados antes da persistência.
- Suporte a compras parceladas.
- Escrita em lote no Google Sheets para compras parceladas.
- Restrição de acesso por `AUTHORIZED_CHAT_IDS`.
- Proteção contra formula injection em textos enviados para a planilha.

## Fluxo

```text
Usuário no Telegram
        ↓
main.py
        ↓
ai_service.py
        ↓
models.py + validators.py
        ↓
sheets_service.py
        ↓
Google Sheets
```

`main.py` inicializa o bot, registra os handlers do Telegram e orquestra os fluxos de registro e consulta.

`ai_service.py` envia a mensagem ao Gemini, exige JSON estruturado e converte respostas de registro em `RegistroFinanceiro`.

`models.py` contém os modelos de domínio, incluindo a dataclass `RegistroFinanceiro`.

`validators.py` valida data, valor, tipo, categoria, parcelas e descrição antes que o registro chegue ao Google Sheets.

`exceptions.py` centraliza exceções customizadas, como erros de interpretação da IA e entrada inválida.

`sheets_service.py` conecta ao Google Sheets, consulta registros e grava movimentações. Para compras parceladas, monta todas as linhas em memória e usa uma única chamada `insert_rows` com retry envolvendo o lote inteiro.

## Tecnologias

- Python 3
- Telegram via `pyTelegramBotAPI`
- Gemini via `google-genai`
- Google Sheets via `gspread`
- Google Auth
- `python-dotenv`

## Estrutura

```text
.
├── main.py
├── config.py
├── ai_service.py
├── sheets_service.py
├── models.py
├── validators.py
├── exceptions.py
├── scripts/
│   └── teste_gemini.py
├── requirements.txt
├── .env.example
├── .gitignore
├── LICENSE
└── README.md
```

## Pré-Requisitos

- Python 3.10 ou superior.
- Bot criado no Telegram e token disponível.
- Chave da API Gemini.
- Projeto no Google Cloud com Google Sheets API habilitada.
- Conta de serviço do Google Cloud com arquivo JSON de credenciais.
- Planilha compartilhada com o e-mail da conta de serviço.

## Instalação

Clone o repositório e entre na pasta:

```bash
git clone <url-do-repositorio>
cd financeirane-ai-agent
```

Crie e ative o ambiente virtual:

```bash
python3 -m venv venv
source venv/bin/activate
```

Instale as dependências:

```bash
pip install -r requirements.txt
```

## Variáveis De Ambiente

Crie um arquivo `.env` na raiz do projeto usando `.env.example` como referência:

```env
TELEGRAM_TOKEN=1234567890:telegram_token_ficticio
GEMINI_API_KEY=gemini_api_key_ficticia
AUTHORIZED_CHAT_IDS=123456789,987654321
GOOGLE_CREDENTIALS_FILE=credenciais.json
SPREADSHEET_NAME=Financeirane
```

Não use valores reais no `.env.example`. O arquivo `.env` local não deve ser versionado.

## Credenciais Do Google Sheets

1. Crie um projeto no Google Cloud.
2. Habilite a Google Sheets API.
3. Crie uma conta de serviço.
4. Baixe o JSON de credenciais.
5. Salve o arquivo localmente como `credenciais.json`, ou ajuste `GOOGLE_CREDENTIALS_FILE`.
6. Compartilhe a planilha com o e-mail da conta de serviço.

Nunca versione `credenciais.json`.

## Formato Da Planilha

A primeira aba da planilha deve conter um cabeçalho na primeira linha:

```text
Data | Tipo | Valor | Descricao | Parcelas | Categoria
```

O formato de data usado pelo projeto é `DD/MM/AAAA`.

Os registros novos são inseridos a partir da linha 2. Em compras parceladas, cada parcela vira uma linha, com descrição indicando `Parcela 1/N`, `Parcela 2/N` e assim por diante.

## Execução

Com o ambiente virtual ativo:

```bash
python3 main.py
```

Para testar a chave Gemini e listar modelos disponíveis:

```bash
python3 scripts/teste_gemini.py
```

## Exemplos De Mensagens

```text
gastei 42 no mercado
```

```text
comprei uma cadeira de 600 reais em 4 vezes
```

```text
recebi 1500 de freelas
```

```text
quanto eu tenho para pagar este mês?
```

```text
quanto gastei em junho de 2026?
```

Para descobrir o ID do chat autorizado:

```text
/id
```

ou:

```text
/meu_id
```

## Segurança E Privacidade

- Não versione `.env`.
- Não versione `credenciais.json`.
- Não publique tokens do Telegram.
- Não publique chaves Gemini.
- Não inclua dados financeiros reais em commits, issues ou documentação.
- Use `AUTHORIZED_CHAT_IDS` para restringir o acesso ao bot.
- Revise logs antes de compartilhá-los.

O `.gitignore` já cobre arquivos sensíveis e artefatos locais comuns, incluindo `.env`, `credenciais.json`, `venv/`, caches Python e arquivos `.pyc`.

## Limitações Atuais

- O Google Sheets não oferece transação real como um banco de dados relacional.
- A escrita de parcelas é feita em lote para reduzir gravações parciais causadas pela aplicação, mas não há rollback transacional caso a API aplique uma escrita parcial internamente.
- A interpretação depende da resposta do Gemini e das regras do prompt.
- A aplicação é voltada para uso pessoal e uma planilha configurada.
- Consultas atuais focam em gastos por período.

## Próximos Passos

- Criar testes unitários para validações e serviços.
- Melhorar mensagens de erro para o usuário final.
- Adicionar relatórios por categoria.
- Adicionar resumos automáticos.
- Suportar múltiplas abas ou múltiplos usuários.
- Avaliar persistência transacional em banco de dados dedicado.

## Licença

Este projeto está licenciado sob a licença MIT. Consulte [LICENSE](LICENSE).
