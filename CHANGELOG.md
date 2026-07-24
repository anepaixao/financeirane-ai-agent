# Changelog

Todas as mudanças relevantes deste projeto serão documentadas neste arquivo.

O formato segue os princípios do [Keep a Changelog](https://keepachangelog.com/), e o projeto utiliza versionamento semântico.

## [1.0.0] - 2026-07-24

### Adicionado

* Bot financeiro pessoal integrado ao Telegram.
* Interpretação de mensagens em linguagem natural com Google Gemini.
* Registro de gastos e receitas no Google Sheets.
* Consulta de gastos por mês e ano.
* Modelo de domínio `RegistroFinanceiro`.
* Validações para data, valor, tipo, categoria, descrição e parcelamento.
* Exceções customizadas para erros de entrada e interpretação da IA.
* Restrição de acesso por meio de `AUTHORIZED_CHAT_IDS`.
* Comandos para consulta do identificador do usuário no Telegram.
* Proteção contra formula injection em textos enviados para a planilha.
* Suporte a compras parceladas.
* Escrita em lote de parcelas com `insert_rows`.
* Retry com espera progressiva para operações no Google Sheets.
* Configuração por variáveis de ambiente.
* Arquivo `.env.example` com valores fictícios.
* Documentação de instalação, configuração, execução e segurança.
* Deploy em uma instância Ubuntu na Oracle Cloud Infrastructure.

### Alterado

* Organização do código em serviços, modelos, validadores e exceções.
* Inicialização do bot extraída para funções testáveis em `main.py`.
* Registro de handlers separado da inicialização da aplicação.
* Validação dos dados movida para uma camada própria.
* Persistência de compras parceladas alterada de múltiplas escritas para uma única operação em lote.
* Cálculo de parcelas alterado para utilizar centavos inteiros.
* Distribuição dos centavos restantes entre as primeiras parcelas.
* Padronização do nome do projeto como FinanceirAne.
* README atualizado para representar o estado real da versão 1.0.0.

### Corrigido

* Divergências entre o valor total de uma compra e a soma das parcelas.
* Possíveis erros de precisão causados por números de ponto flutuante.
* Substituição automática e indevida de anos em registros financeiros.
* Problemas de organização e duplicação na documentação.
* Erros de digitação e formatação no README.

### Segurança

* Credenciais e tokens removidos da documentação e dos arquivos versionados.
* Orientações adicionadas para não versionar `.env` e credenciais do Google.
* Acesso ao bot limitado a usuários autorizados.
* Entradas de texto sanitizadas antes do envio ao Google Sheets.

### Limitações conhecidas

* O Google Sheets não fornece transações reais nem rollback.
* A aplicação está configurada para uso pessoal.
* As consultas atuais são concentradas em gastos por período.
* A interpretação das mensagens depende da resposta do modelo Gemini.
* Ainda não existem testes automatizados nem integração contínua.

[1.0.0]: https://github.com/anepaixao/financeirane-ai-agent/releases/tag/v1.0.0
