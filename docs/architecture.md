# Arquitetura Técnica da FinanceirAne

Este documento descreve a arquitetura atual da FinanceirAne e propõe uma migração incremental para um layout de pacote em `src/financeirane/`.

O objetivo é orientar evolução técnica sem executar uma migração agora, sem alterar comportamento funcional e sem criar um big-bang refactor.

## Visão Geral

A FinanceirAne é um bot financeiro pessoal executado em Python. A interface atual é o Telegram, a interpretação de linguagem natural é feita pelo Gemini e a persistência atual é uma planilha do Google Sheets.

Fluxo principal de registro:

```text
Usuário no Telegram
        ↓
main.py
        ↓
ai_service.py
        ↓
RegistroFinanceiro + validators.py
        ↓
sheets_service.py
        ↓
Google Sheets
```

Fluxo principal de consulta:

```text
Usuário no Telegram
        ↓
main.py
        ↓
ai_service.py
        ↓
dict com intenção consultar, mês e ano
        ↓
sheets_service.py
        ↓
Google Sheets
        ↓
resposta formatada para Telegram
```

## Pontos De Entrada

- `main.py`: entry point da aplicação.
- `main.main()`: configura logging, cria o bot e inicia `infinity_polling()`.
- `main.criar_bot()`: conecta ao Google Sheets, cria `telebot.TeleBot` e registra handlers.
- `main.registrar_handlers(bot, planilha)`: registra o handler que processa mensagens recebidas.

## Mapa De Módulos

```text
main.py
├── logging_config.py
├── config.py
├── ai_service.py
├── models.py
└── sheets_service.py

ai_service.py
├── config.py
├── exceptions.py
├── logging_config.py
├── models.py
├── validators.py
└── google-genai

sheets_service.py
├── config.py
├── logging_config.py
├── gspread
└── biblioteca padrão: calendar, datetime, decimal, logging, time

validators.py
├── config.py
├── exceptions.py
├── models.py
└── datetime

config.py
├── python-dotenv
├── os
└── logging

logging_config.py
├── logging
├── os
└── time.perf_counter
```

## Dependências Entre Módulos

- `main.py -> logging_config.py`: configuração e helpers de observabilidade.
- `main.py -> config.py`: token, usuários autorizados e limite de mensagem.
- `main.py -> ai_service.py`: interpretação da mensagem.
- `main.py -> models.py`: diferenciação entre registro e consulta.
- `main.py -> sheets_service.py`: persistência e consulta.
- `ai_service.py -> config.py`: chave Gemini e categorias permitidas.
- `ai_service.py -> models.py`: criação de `RegistroFinanceiro`.
- `ai_service.py -> validators.py`: validação do registro antes de sair do serviço de IA.
- `ai_service.py -> exceptions.py`: erros de interpretação.
- `sheets_service.py -> config.py`: credenciais, nome da planilha, categorias, tipos e limite de parcelas.
- `sheets_service.py -> logging_config.py`: duração de operações.
- `validators.py -> config.py`: categorias, tipos e limite de parcelas.

Acoplamentos relevantes:

- `ai_service.py` instancia `genai.Client` em nível de módulo.
- `sheets_service.py` conhece diretamente `gspread` e o formato da planilha.
- `main.py` orquestra Telegram, IA e Google Sheets no mesmo handler.
- `validators.py` depende de constantes de `config.py`, misturando regra de domínio com configuração global.
- `config.py` valida variáveis obrigatórias durante import.

## Responsabilidades Atuais

| Módulo | Responsabilidade principal | Responsabilidades secundárias | Delimitação | Risco de manutenção |
| --- | --- | --- | --- | --- |
| `main.py` | Interface Telegram e orquestração do fluxo | Autorização, comandos, mensagens de erro, inicialização | Boa para o tamanho atual, mas concentra interface e caso de uso | Médio |
| `ai_service.py` | Interpretar mensagem com Gemini | Prompt, parsing JSON, criação e validação de `RegistroFinanceiro`, logs | Parcialmente delimitado; mistura integração externa e normalização de resposta | Médio |
| `sheets_service.py` | Persistir e consultar Google Sheets | Retry, backoff, cálculo de parcelas, sanitização, formatação de resposta | Funcional, mas mistura repositório, regras financeiras e apresentação | Alto |
| `validators.py` | Validar regras de negócio | Uso de categorias/tipos configurados | Bem delimitado para o MVP | Baixo |
| `models.py` | Modelo de domínio | Nenhuma relevante | Bem delimitado | Baixo |
| `exceptions.py` | Exceções customizadas | Nenhuma relevante | Bem delimitado | Baixo |
| `config.py` | Configuração via ambiente | Validação em import e constantes de domínio | Útil, mas com efeito colateral no import | Médio |
| `logging_config.py` | Configuração e helpers de logging | Mascaramento de IDs e medição de duração | Bem delimitado | Baixo |

## Fronteiras Atuais

A estrutura atual é uma arquitetura plana por módulos, com separação pragmática por responsabilidade. Ela não implementa Clean Architecture, Hexagonal Architecture ou DDD formal.

O que existe de fato:

- Domínio simples: `models.py`, `validators.py`, `exceptions.py`.
- Aplicação/orquestração: `main.py`.
- Integração com IA: `ai_service.py`.
- Integração com persistência: `sheets_service.py`.
- Configuração e observabilidade: `config.py`, `logging_config.py`.
- Testes automatizados cobrindo fluxos principais e utilitários.

## Dependências Externas

| Dependência | Uso |
| --- | --- |
| `pyTelegramBotAPI` | Interface com Telegram. |
| `google-genai` | Cliente Gemini. |
| `gspread` | Acesso ao Google Sheets. |
| `google-auth`, `google-auth-oauthlib` | Autenticação Google. |
| `python-dotenv` | Carregamento de variáveis de ambiente. |
| `pytest`, `pytest-cov` | Testes e cobertura. |
| `ruff` | Lint e formatação. |
| `pre-commit` | Hooks locais de qualidade. |

## Pontos Fortes Atuais

- Cobertura de testes alta nos módulos críticos.
- Validação de domínio antes da persistência.
- Exceções customizadas para interpretação da IA e entrada inválida.
- Escrita em lote no Google Sheets para compras parceladas.
- Cálculo financeiro em centavos inteiros, com distribuição dos centavos restantes.
- Sanitização contra formula injection.
- Retry com backoff para falhas transitórias do Google Sheets.
- Logging estruturado com duração, operação e política de privacidade.
- Autorização por `AUTHORIZED_CHAT_IDS`.
- CI com Ruff, formatação e pytest.
- Pre-commit configurado com Ruff.
- Inicialização de `main.py` testável, sem polling no import.

## Dívidas E Limitações

### Alta Prioridade

- `sheets_service.py` mistura persistência, regra financeira, parsing de consulta e formatação de resposta.
- `main.py` concentra interface Telegram e caso de uso, o que dificulta adicionar novas interfaces.
- Google Sheets é a persistência atual e não oferece transações reais.

### Média Prioridade

- `ai_service.py` instancia o cliente Gemini em nível de módulo.
- `config.py` executa validação durante import.
- Categorias e tipos ficam em `config.py`, embora sejam conceitos de domínio.
- A resposta de consulta ainda usa `dict`; registro usa `RegistroFinanceiro`.
- Imports ainda assumem módulos na raiz, o que dificulta migração direta para pacote.

### Baixa Prioridade

- Estrutura plana é suficiente para o MVP, mas fica menos clara conforme novos recursos entrarem.
- `scripts/teste_gemini.py` é utilitário operacional fora do pacote.
- Algumas mensagens de usuário são montadas dentro de serviços, não em uma camada de apresentação.

## Arquitetura-Alvo Incremental

Uma estrutura futura possível, ajustada ao tamanho atual do projeto:

```text
src/
└── financeirane/
    ├── __init__.py
    ├── main.py
    ├── config.py
    ├── logging_config.py
    ├── domain/
    │   ├── __init__.py
    │   ├── models.py
    │   ├── validators.py
    │   └── exceptions.py
    ├── services/
    │   ├── __init__.py
    │   ├── ai_service.py
    │   └── finance_service.py
    ├── repositories/
    │   ├── __init__.py
    │   └── sheets_repository.py
    └── interfaces/
        ├── __init__.py
        └── telegram_bot.py
```

Essa estrutura não deve ser criada de uma vez. O alvo é separar responsabilidades gradualmente:

- `domain/`: modelos, validações e exceções.
- `services/`: casos de uso e integrações de aplicação.
- `repositories/`: persistência em Google Sheets hoje, outra persistência no futuro.
- `interfaces/`: Telegram hoje, outras interfaces no futuro.
- `config.py` e `logging_config.py`: infraestrutura transversal mínima.

## Plano De Migração Incremental

### Fase 1: Preparar Imports Para Pacote

- Objetivo: mapear imports atuais e reduzir dependência de imports implícitos da raiz.
- Arquivos envolvidos: documentação, testes e eventualmente imports em módulos existentes.
- Risco: baixo.
- Testes que protegem: suíte completa de 165 testes.
- Critério de conclusão: mapa de imports validado e estratégia definida.
- Rollback: reverter apenas ajustes de imports se houver alteração.

### Fase 2: Criar Pacote Vazio

- Objetivo: criar `src/financeirane/__init__.py` sem mover lógica.
- Arquivos envolvidos: `src/financeirane/__init__.py`, configuração de pytest/Ruff se necessário.
- Risco: baixo.
- Testes que protegem: pytest completo, Ruff e pre-commit.
- Critério de conclusão: pacote importável sem alterar execução atual.
- Rollback: remover diretório `src/`.

### Fase 3: Migrar Domínio

- Objetivo: mover `models.py`, `validators.py` e `exceptions.py` para `financeirane/domain/`.
- Arquivos envolvidos: domínio, imports e testes correspondentes.
- Risco: médio.
- Testes que protegem: `tests/test_validators.py`, `tests/test_ai_service.py`, `tests/test_sheets_service.py`.
- Critério de conclusão: domínio importável pelo pacote e comportamento preservado.
- Rollback: restaurar arquivos na raiz e imports anteriores.

### Fase 4: Migrar Configuração E Logging

- Objetivo: mover `config.py` e `logging_config.py` para o pacote, mantendo compatibilidade de execução.
- Arquivos envolvidos: configuração, logging, entry point e testes.
- Risco: médio.
- Testes que protegem: `tests/test_config.py`, `tests/test_logging_config.py`, `tests/test_main_handlers.py`.
- Critério de conclusão: `LOG_LEVEL`, `.env`, logging e validação de ambiente funcionando como antes.
- Rollback: retornar módulos à raiz.

### Fase 5: Migrar Integração Gemini

- Objetivo: mover `ai_service.py` para `services/` ou `integrations/`, sem mudar prompt ou modelo.
- Arquivos envolvidos: `ai_service.py`, imports e testes.
- Risco: médio.
- Testes que protegem: `tests/test_ai_service.py`.
- Critério de conclusão: Gemini mockado nos testes, modelo preservado e sem chamada real.
- Rollback: restaurar módulo e imports.

### Fase 6: Separar Persistência Google Sheets

- Objetivo: transformar `sheets_service.py` em repositório/adaptador, preservando regras financeiras já testadas.
- Arquivos envolvidos: `sheets_service.py`, possível `repositories/sheets_repository.py`, testes.
- Risco: alto.
- Testes que protegem: `tests/test_sheets_service.py`, `tests/test_sheets_utils.py`.
- Critério de conclusão: lote, retry, centavos, consulta e sanitização preservados.
- Rollback: manter `sheets_service.py` atual.

### Fase 7: Separar Orquestração Da Interface Telegram

- Objetivo: extrair caso de uso de registro/consulta para serviço de aplicação, deixando Telegram como adapter.
- Arquivos envolvidos: `main.py`, possível `interfaces/telegram_bot.py`, possível `services/finance_service.py`.
- Risco: alto.
- Testes que protegem: `tests/test_main_handlers.py`, testes de serviços novos.
- Critério de conclusão: comportamento do bot preservado, sem chamadas reais em testes.
- Rollback: retornar lógica ao `main.py`.

### Fase 8: Atualizar Entry Point

- Objetivo: permitir execução por pacote sem quebrar `python main.py` até a transição ser concluída.
- Arquivos envolvidos: `main.py`, possível `financeirane/main.py`, README.
- Risco: médio.
- Testes que protegem: testes de inicialização e CI.
- Critério de conclusão: execução antiga e nova documentadas durante período de compatibilidade.
- Rollback: manter apenas entry point atual.

## Decisões Que Merecem ADR

- Usar Google Sheets como persistência atual do MVP.
- Manter Gemini como camada de interpretação, não como fonte de verdade de regras de negócio.
- Validar dados da IA antes da persistência.
- Registrar compras parceladas em lote com `insert_rows`.
- Usar Telegram como adapter principal de interface.
- Adotar layout `src/financeirane/` de forma incremental.
- Criar ou não uma abstração de repositório antes de trocar persistência.
- Manter logging em texto estruturado, sem JSON logs nesta etapa.
- Manter autorização por `AUTHORIZED_CHAT_IDS` para uso pessoal.

## O Que Não Fazer

- Não fazer big-bang refactor.
- Não mover todos os arquivos para `src/` em uma única mudança.
- Não introduzir framework web sem necessidade real.
- Não criar interfaces ou classes abstratas sem pelo menos duas implementações ou um caso concreto.
- Não trocar Google Sheets apenas por estética arquitetural.
- Não quebrar módulos só para aumentar pureza.
- Não alterar prompt, modelo Gemini ou formato da planilha durante migração estrutural.
- Não misturar migração arquitetural com mudanças de regra financeira.
- Não reduzir testes, logging ou proteção contra vazamento de dados.

## Critérios De Segurança Para Refatoração

Toda fase de migração deve preservar:

- suíte completa verde;
- CI com Ruff, Ruff Format e pytest;
- pre-commit passando;
- nenhuma chamada real a Telegram, Gemini ou Google Sheets nos testes;
- nenhuma exposição de `.env`, tokens, chaves, credenciais ou dados financeiros reais;
- comportamento externo do bot;
- formato da planilha;
- escrita em lote de parcelas;
- cálculo em centavos;
- sanitização contra formula injection;
- política de logs sem dados sensíveis.

Antes de cada fase:

```bash
venv/bin/python -m pytest -v
venv/bin/python -m ruff check .
venv/bin/python -m ruff format --check .
venv/bin/python -m pre_commit run --all-files
git diff --check
```

Depois de cada fase, comparar o comportamento observado do bot em um ambiente de teste controlado antes de promover a mudança.
