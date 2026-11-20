# 004. API: FastAPI com Runner e App assíncronos

- **Status:** aceita
- **Data:** 2026-11-20

## Contexto

O enunciado exige uma API HTTP em `localhost:8000` que segue um contrato fixo (criar sessão, enviar mensagem, responder confirmação, listar eventos e rotas de verificação). Ela precisa executar o assistente com o Runner do ADK e atender requisições simultâneas, como as duas aprovações do passo 14.

## Decisão

- **FastAPI**, servido por **uvicorn**. É o framework usado no curso e tem suporte nativo a `async`.
- **Execução personalizada** com `Runner` e `App` do ADK, e não a API pronta do `adk web`/`adk api_server`. O contrato da API é nosso, e a rota de confirmações exige controlar a retomada da execução.
- **Padrão assíncrono** de ponta a ponta (`async def`, `Runner.run_async`, driver assíncrono do Postgres), para não bloquear o servidor enquanto o modelo responde.
- O processo da API é **sem estado próprio**: tudo o que precisa sobreviver ao reinício fica no banco (decisão 003).

## Alternativas descartadas

- **`adk api_server`**: expõe rotas próprias do ADK, que não seguem o nosso contrato.
- **Flask/Django**: sem vantagem aqui e menos naturais para código assíncrono.

## Consequências

- A tradução entre o contrato HTTP e os eventos do ADK (por exemplo, converter um pedido de confirmação em `confirmacoes_pendentes`) é código nosso, e é onde mora a parte mais delicada do projeto.
- Toda a camada de dados precisa ser assíncrona.
