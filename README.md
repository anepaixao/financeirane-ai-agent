# FinanceirAne AI Agent

**Versão atual:** v1.0.0 — MVP concluído
**Deploy:** executando em uma instância Oracle Cloud Infrastructure (OCI) para uso pessoal.

FinanceirAne AI Agent é um bot financeiro pessoal para Telegram. Ele interpreta mensagens em linguagem natural com Gemini, valida os dados no domínio da aplicação e registra ou consulta movimentações em uma planilha do Google Sheets.

O sistema serve para registro e consulta de movimentações financeiras pessoais. Ele não fornece aconselhamento financeiro, recomendação de investimento, análise patrimonial ou orientação profissional.

As mensagens, valores, IDs e credenciais apresentados nesta documentação são fictícios e servem apenas como exemplos.

## Status Da Versão

- Versão atual: V1.0.0.
- Status: MVP concluído.
- Foco: uso pessoal e portfólio.
- Próxima etapa: V2.

## Problema

Registrar gastos manualmente em planilhas é trabalhoso e fácil de esquecer. A FinanceirAne reduz esse atrito: a pessoa envia uma frase comum pelo Telegram e o agente transforma a mensagem em um registro estruturado, validado e persistido.

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

`sheets_service.py` conecta ao Google Sheets, consulta registros e grava movimentações. Para compras parceladas, converte o valor total para centavos inteiros, distribui os centavos restantes entre as primeiras parcelas, monta todas as linhas em memória e usa uma única chamada `insert_rows` com retry envolvendo o lote inteiro. Assim, a soma das parcelas é exatamente igual ao valor total informado.

## Arquitetura de Soluções

Usuário
    │
Telegram Bot
    │
FinanceirAne
(Oracle Cloud / Ubuntu)
    │
 ├── Google Gemini API
 └── Google Sheets API

## Tecnologias

- Python 3
- Telegram via `pyTelegramBotAPI`
- Gemini via `google-genai`
- Google Sheets via `gspread`
- Google Auth
- `python-dotenv`

| Camada | Tecnologia |
|--------|------------|
| Linguagem | Python 3.12 |
| Interface | Telegram Bot API |
| IA | Google Gemini |
| Persistência | Google Sheets |
| Infraestrutura | Oracle Cloud Infrastructure (OCI) |
| Sistema Operacional | Ubuntu Linux |
| Configuração | python-dotenv |


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

## Infraestrutura

A FinanceirAne pode ser executada localmente durante o desenvolvimento ou permanecer ativa em uma instância Linux na Oracle Cloud Infrastructure (OCI).

Ambiente utilizado:

- Oracle Cloud Infrastructure (OCI)
- Ubuntu Linux
- Python 3.12
- Ambiente virtual (`venv`)
- Execução contínua do bot Telegram
- Google Sheets como camada de persistência
- Google Gemini para interpretação das mensagens

As credenciais permanecem armazenadas localmente na instância e não fazem parte do repositório.

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
python -m pip install -r requirements.txt
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

Para evitar erros de ponto flutuante, o valor total é convertido para centavos inteiros antes da divisão. Os centavos restantes são distribuídos entre as primeiras parcelas. Por exemplo, R$ 100,00 em 3 parcelas gera `33,34`, `33,33` e `33,33`, mantendo a soma exatamente igual a R$ 100,00.

As linhas de uma compra parcelada são gravadas em uma única chamada `insert_rows`, reduzindo o risco de gravação parcial causada por loops de escrita na aplicação.

## Execução

Com o ambiente virtual ativo:

```bash
python main.py
```

Para testar a chave Gemini e listar modelos disponíveis:

```bash
python scripts/teste_gemini.py
```

## Verificações Locais

```bash
python -m compileall .
```

```bash
python -m py_compile main.py ai_service.py sheets_service.py models.py validators.py exceptions.py
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

- Testes automatizados com pytest.
- Integração contínua com GitHub Actions.
- Tratamento específico de exceções.
- Relatórios e análises financeiras.
- Dashboard interativo.
- Melhorias na experiência do Telegram.
- Avaliação futura de banco de dados relacional.
- Monitoramento e observabilidade da instância Oracle Cloud.

## Licença

Este projeto está licenciado sob a licença MIT. Consulte [LICENSE](LICENSE).
