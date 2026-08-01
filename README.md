# FinanceirAne

> Bot financeiro pessoal com IA para registrar e consultar movimentações pelo Telegram.

## 🧾 Descrição do projeto

FinanceirAne é um agente financeiro pessoal integrado ao Telegram. O bot interpreta mensagens em linguagem natural com Google Gemini, transforma a intenção do usuário em dados estruturados, valida esses dados no domínio da aplicação e registra ou consulta movimentações em uma planilha do Google Sheets.

O projeto foi criado para uso pessoal e portfólio. Ele auxilia no registro e na consulta de gastos e receitas, mas não fornece aconselhamento financeiro, recomendação de investimento, análise patrimonial ou orientação profissional.

As mensagens, valores, IDs e credenciais apresentados nesta documentação são fictícios e servem apenas como exemplos.

| Item | Status |
| --- | --- |
| Versão atual | v1.0.0 |
| Status | MVP concluído |
| Foco | Uso pessoal e portfólio |
| Próxima etapa | V2 |
| Repositório | `financeirane-ai-agent` |

## 🎯 Objetivo

Reduzir o atrito de registrar finanças pessoais em planilhas. Em vez de abrir o Google Sheets e preencher linhas manualmente, a pessoa envia mensagens como:

```text
gastei 42 no mercado
```

ou:

```text
comprei uma cadeira de 600 reais em 4 vezes
```

A FinanceirAne interpreta a mensagem, valida os campos e grava os dados de forma organizada.

## ✨ Principais funcionalidades

- Registro de gastos e receitas por texto livre no Telegram.
- Consulta de gastos por mês e ano.
- Interpretação de linguagem natural com Google Gemini.
- Conversão da resposta da IA para o modelo de domínio `RegistroFinanceiro`.
- Validação de data, valor, tipo, categoria, descrição e parcelas antes da persistência.
- Categorias permitidas centralizadas em `config.py`.
- Suporte a compras parceladas.
- Cálculo de parcelas usando centavos inteiros para evitar erros de ponto flutuante.
- Distribuição dos centavos restantes entre as primeiras parcelas.
- Escrita em lote de parcelas no Google Sheets com `insert_rows`.
- Retry com backoff progressivo para falhas transitórias do Google Sheets.
- Sanitização contra formula injection em textos enviados para a planilha.
- Restrição de acesso por `AUTHORIZED_CHAT_IDS`.
- Comandos `/id` e `/meu_id` para descobrir o ID do usuário/chat.
- Inicialização do bot organizada em funções testáveis.
- Base inicial de testes automatizados com pytest.

## 🏗️ Arquitetura atual

```text
Usuário no Telegram
        ↓
main.py
        ↓
ai_service.py
        ↓
models.py + validators.py + exceptions.py
        ↓
sheets_service.py
        ↓
Google Sheets
```

| Módulo | Responsabilidade |
| --- | --- |
| `main.py` | Inicializa o bot, registra handlers e orquestra os fluxos de registro e consulta. |
| `config.py` | Carrega variáveis de ambiente e constantes da aplicação. |
| `ai_service.py` | Envia mensagens ao Gemini, exige JSON estruturado e instancia `RegistroFinanceiro`. |
| `models.py` | Define modelos de domínio, como a dataclass `RegistroFinanceiro`. |
| `validators.py` | Valida regras de negócio antes da persistência. |
| `exceptions.py` | Centraliza exceções customizadas do domínio e da IA. |
| `sheets_service.py` | Conecta ao Google Sheets, consulta registros e persiste movimentações. |
| `tests/` | Contém testes automatizados com pytest. |
| `scripts/teste_gemini.py` | Lista modelos disponíveis para a chave Gemini configurada. |

### Infraestrutura

A FinanceirAne pode ser executada localmente durante o desenvolvimento ou em uma instância Linux. O ambiente usado no MVP inclui:

- Oracle Cloud Infrastructure (OCI).
- Ubuntu Linux.
- Python 3.12.
- Ambiente virtual (`venv`).
- Execução contínua do bot Telegram.
- Google Sheets como persistência.
- Google Gemini para interpretação das mensagens.

As credenciais permanecem armazenadas localmente na máquina/instância e não fazem parte do repositório.

## 🧰 Tecnologias utilizadas

| Camada | Tecnologia |
| --- | --- |
| Linguagem | Python 3.10+ |
| Interface | Telegram Bot API via `pyTelegramBotAPI` |
| IA | Google Gemini via `google-genai` |
| Persistência | Google Sheets via `gspread` |
| Autenticação Google | `google-auth` e `google-auth-oauthlib` |
| Configuração | `python-dotenv` |
| Testes | `pytest` e `unittest.mock` |
| Infraestrutura do MVP | Oracle Cloud Infrastructure + Ubuntu Linux |

## 📁 Estrutura do projeto

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
├── tests/
│   ├── __init__.py
│   ├── test_config.py
│   ├── test_main_handlers.py
│   ├── test_sheets_utils.py
│   └── test_validators.py
├── requirements.txt
├── .env.example
├── .gitignore
├── CHANGELOG.md
├── LICENSE
└── README.md
```

## ✅ Pré-requisitos

- Python 3.10 ou superior.
- Conta no Telegram.
- Bot criado no Telegram pelo BotFather.
- Chave da API Gemini.
- Projeto no Google Cloud com Google Sheets API habilitada.
- Conta de serviço do Google Cloud com arquivo JSON de credenciais.
- Planilha compartilhada com o e-mail da conta de serviço.

## ⚙️ Instalação

Clone o repositório:

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
python -m pip install -r requirements.txt
```

Instale os hooks de pre-commit:

```bash
python -m pre_commit install
```

## 🔐 Configuração do `.env`

Crie um arquivo `.env` na raiz do projeto usando `.env.example` como referência:

```env
TELEGRAM_TOKEN=1234567890:telegram_token_ficticio
GEMINI_API_KEY=gemini_api_key_ficticia
AUTHORIZED_CHAT_IDS=123456789,987654321
GOOGLE_CREDENTIALS_FILE=credenciais.json
SPREADSHEET_NAME=Financeirane
```

| Variável | Obrigatória | Descrição |
| --- | --- | --- |
| `TELEGRAM_TOKEN` | Sim | Token do bot Telegram. |
| `GEMINI_API_KEY` | Sim | Chave da API Gemini. |
| `AUTHORIZED_CHAT_IDS` | Recomendado | IDs autorizados a usar o bot, separados por vírgula. |
| `GOOGLE_CREDENTIALS_FILE` | Não | Caminho do JSON da conta de serviço. Padrão: `credenciais.json`. |
| `SPREADSHEET_NAME` | Não | Nome da planilha. Padrão: `Financeirane`. |

Nunca use valores reais no `.env.example`. O arquivo `.env` local não deve ser versionado.

## 🤖 Como obter o `TELEGRAM_TOKEN`

1. Abra o Telegram.
2. Procure por `@BotFather`.
3. Envie o comando:

```text
/newbot
```

4. Escolha um nome e um username para o bot.
5. Copie o token gerado pelo BotFather.
6. Adicione o token ao `.env`:

```env
TELEGRAM_TOKEN=1234567890:telegram_token_ficticio
```

Para descobrir o ID do usuário/chat autorizado, execute o bot e envie:

```text
/id
```

ou:

```text
/meu_id
```

## 🧠 Como obter o `GEMINI_API_KEY`

1. Acesse o Google AI Studio.
2. Crie ou selecione uma chave de API para Gemini.
3. Copie a chave gerada.
4. Adicione a chave ao `.env`:

```env
GEMINI_API_KEY=gemini_api_key_ficticia
```

Para verificar os modelos disponíveis para a chave configurada:

```bash
python scripts/teste_gemini.py
```

## 📊 Como configurar o Google Sheets

1. Crie um projeto no Google Cloud.
2. Habilite a Google Sheets API.
3. Crie uma conta de serviço.
4. Baixe o arquivo JSON de credenciais.
5. Salve o arquivo localmente como `credenciais.json`, ou ajuste `GOOGLE_CREDENTIALS_FILE`.
6. Crie uma planilha com o nome definido em `SPREADSHEET_NAME`.
7. Compartilhe a planilha com o e-mail da conta de serviço.

Nunca versione `credenciais.json`.

### Formato esperado da planilha

A primeira aba da planilha deve conter este cabeçalho na primeira linha:

```text
Data | Tipo | Valor | Descricao | Parcelas | Categoria
```

| Coluna | Exemplo | Observação |
| --- | --- | --- |
| `Data` | `25/07/2026` | Formato `DD/MM/AAAA`. |
| `Tipo` | `gasto` | Valores aceitos: `gasto` ou `receita`. |
| `Valor` | `33,34` | Usa vírgula decimal. |
| `Descricao` | `Mercado` | Texto sanitizado antes da escrita. |
| `Parcelas` | `3` | Inteiro entre `1` e `MAX_PARCELAS`. |
| `Categoria` | `Feira` | Deve estar em `CATEGORIAS_PERMITIDAS`. |

Os registros novos são inseridos a partir da linha 2. Em compras parceladas, cada parcela vira uma linha, com descrição indicando `Parcela 1/N`, `Parcela 2/N` e assim por diante.

Para evitar erros de ponto flutuante, o valor total é convertido para centavos inteiros antes da divisão. Os centavos restantes são distribuídos entre as primeiras parcelas. Por exemplo, R$ 100,00 em 3 parcelas gera:

```text
33,34
33,33
33,33
```

A soma das parcelas é exatamente igual a R$ 100,00. As linhas de uma compra parcelada são gravadas em uma única chamada `insert_rows`, reduzindo o risco de gravação parcial causada por loops de escrita na aplicação.

O Google Sheets não oferece transação real nem rollback. A escrita em lote melhora a atomicidade no nível da aplicação, mas não substitui uma transação de banco de dados.

## ▶️ Como executar

Com o ambiente virtual ativo:

```bash
python main.py
```

Exemplos de mensagens aceitas:

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

## 🧪 Como executar os testes

A base de testes usa pytest.

Execute as verificações de lint e formatação:

```bash
python -m ruff check .
```

```bash
python -m ruff format --check .
```

Formate os arquivos Python localmente quando necessário:

```bash
python -m ruff format .
```

Execute os hooks de pre-commit em todos os arquivos:

```bash
python -m pre_commit run --all-files
```

Os hooks executam lint e verificação/formatação com Ruff antes do commit. Eles não executam pytest; a suíte completa continua rodando manualmente e na CI.

Execute a suíte completa:

```bash
python -m pytest -v
```

Execute verificações rápidas de compilação:

```bash
python -m compileall .
```

```bash
python -m py_compile main.py ai_service.py sheets_service.py models.py validators.py exceptions.py
```

Áreas cobertas atualmente:

| Arquivo de teste | Cobertura principal |
| --- | --- |
| `tests/test_config.py` | Parsing de `AUTHORIZED_CHAT_IDS`. |
| `tests/test_main_handlers.py` | Fluxo de autorização e respostas iniciais do Telegram. |
| `tests/test_sheets_utils.py` | Utilitários puros de datas, valores, texto e normalização. |
| `tests/test_validators.py` | Validações de domínio e `RegistroFinanceiro`. |

O CI executa `ruff check .`, `ruff format --check .` e `pytest`.

## 🔒 Como funciona a autorização por `AUTHORIZED_CHAT_IDS`

`AUTHORIZED_CHAT_IDS` define quais usuários podem interagir com o bot. A variável aceita IDs numéricos separados por vírgula:

```env
AUTHORIZED_CHAT_IDS=123456789,987654321
```

Quando uma mensagem chega, `main.py` obtém o ID do usuário com:

```python
user_id = getattr(getattr(message, "from_user", None), "id", None)
```

Se o ID não estiver em `AUTHORIZED_CHAT_IDS`, a mensagem é ignorada. Nesse caso, a aplicação não chama o Gemini, não registra movimentações e não consulta o Google Sheets.

Se `AUTHORIZED_CHAT_IDS` estiver vazio, o bot registra um aviso em log e ignora mensagens de todos os usuários.

## 🔁 Fluxo simplificado do bot

```text
1. Usuário envia mensagem no Telegram
2. main.py verifica se o usuário está autorizado
3. main.py trata comandos rápidos, mensagens vazias e limite de tamanho
4. ai_service.py interpreta a mensagem com Gemini
5. ai_service.py converte registros em RegistroFinanceiro
6. validators.py valida as regras de negócio
7. sheets_service.py registra ou consulta dados no Google Sheets
8. main.py envia a resposta ao usuário no Telegram
```

## 🛡️ Boas práticas

- Não versione `.env`.
- Não versione `credenciais.json`.
- Não publique tokens do Telegram.
- Não publique chaves Gemini.
- Não inclua dados financeiros reais em commits, issues, prints ou documentação.
- Use valores fictícios em exemplos.
- Revise logs antes de compartilhá-los.
- Mantenha `AUTHORIZED_CHAT_IDS` restrito.
- Compartilhe a planilha somente com a conta de serviço necessária.
- Rode os testes antes de alterar fluxos de autorização, validação ou persistência.
- Evite alterar regras de negócio junto com mudanças de documentação.

O `.gitignore` já cobre arquivos sensíveis e artefatos locais comuns, incluindo `.env`, `credenciais.json`, `venv/`, caches Python, `.pytest_cache/` e arquivos `.pyc`.

## ⚠️ Limitações atuais

- O Google Sheets não oferece transações reais nem rollback.
- A interpretação depende da resposta do Gemini e das regras do prompt.
- A aplicação está configurada para uso pessoal e uma planilha.
- As consultas atuais focam em gastos por período.
- Ainda não há dashboard implementado.
- Ainda não há suporte multiusuário completo.
- Ainda não há integração contínua configurada no repositório.

## 🗺️ Roadmap

| Versão | Foco | Status |
| --- | --- | --- |
| V1 | MVP funcional: Telegram, Gemini, Google Sheets, validação, escrita em lote, segurança básica e documentação. | Concluído |
| V2 | Testes automatizados com pytest, integração contínua com GitHub Actions, tratamento específico de exceções e melhorias na experiência do Telegram. | Em evolução |
| V3 | Relatórios e análises financeiras, dashboard interativo, observabilidade e avaliação futura de banco de dados relacional. | Planejado |

## 🤝 Contribuição

Este projeto é pessoal e de portfólio, mas sugestões são bem-vindas. Para contribuir:

1. Abra uma issue descrevendo o problema ou melhoria.
2. Crie uma branch com nome descritivo.
3. Faça alterações pequenas e focadas.
4. Rode os testes.
5. Abra um pull request explicando o contexto e o impacto.

Evite incluir credenciais, dados financeiros reais ou prints com informações sensíveis.

## 📄 Licença

Placeholder: defina aqui a licença oficial do projeto. O repositório inclui um arquivo `LICENSE`; revise-o antes de publicar ou distribuir este software.
