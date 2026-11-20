# 005. Acionamento dos especialistas

- **Status:** provisória (a confirmar no spike da decisão 003)
- **Data:** 2026-11-20

## Contexto

O agente principal precisa acionar os especialistas (decisão 001). O ADK oferece mais de uma forma, e a escolha afeta a Garantia 1: a resposta de confirmação precisa chegar ao agente que pediu a confirmação, e quem escolhe esse agente é o Runner.

## Alternativas

| Opção | Resumo | Pontos fortes | Pontos fracos |
|---|---|---|---|
| A. `sub_agents` | O principal transfere o controle ao especialista | Padrão do ADK para roteador e especialistas; a retomada da confirmação segue a autoria do evento; tool calls ficam nos eventos da sessão | A próxima mensagem pode cair direto no especialista; exige regras de transferência bem definidas |
| B. `AgentTool` | O principal chama o especialista como uma tool e mantém o controle | Fluxo previsível; contexto do principal mais enxuto | Eventos internos podem não aparecer na sessão; confirmação dentro de AgentTool é o cenário de maior risco |
| C. Híbrida | `sub_agents` para reservas e visitantes; `AgentTool` (ou tool de busca) para o regulamento | Cada caso usa o mecanismo mais adequado; o regulamento fica isolado do histórico do principal | Dois mecanismos para explicar e manter |

## Decisão provisória

**Opção C.** Reservas e visitantes, que têm confirmação, usam `sub_agents`. O regulamento, que só consulta, fica isolado, para que os trechos consultados não acompanhem o histórico do principal (Garantia 4).

## Resultado do spike (2026-11-20, ADK 2.9.1, Gemini real, sessão em Postgres)

Topologia testada: principal com um sub_agent (`reservas`) cuja tool exige confirmação.

- **Funciona.** O principal transfere para `reservas`, a tool pede confirmação e nada é executado até a resposta. A aprovação, enviada por um **processo novo** (simulando reinício da API), retoma a execução e grava uma única vez. A negação não executa a tool.
- **Retomada habilitada.** `ResumabilityConfig(is_resumable=True)` no `App` faz o Runner devolver a resposta ao agente que pediu a confirmação. Nesta topologia simples a aprovação também funcionou com `is_resumable=False`, porque o último agente a responder era `reservas`, mas isso depende da topologia. Mantemos a retomada habilitada.
- **O ADK não protege contra resposta repetida.** Uma confirmação **negada** e depois respondida de novo com o mesmo `id` e `confirmed: true` **executou a ação**. O `409` do contrato e a regra "aprovar executa uma única vez" precisam ser garantidos pelo nosso código, a partir das confirmações realmente pendentes na sessão.
- A opção `require_confirmation` aceita uma função, então a confirmação pode ser condicional (por exemplo, só quando a taxa da área é maior que zero).

A opção C (híbrida) continua provisória: o spike cobriu apenas o `sub_agents`. A parte do regulamento ainda não foi testada.

## Como será confirmada

No spike, verificar no código instalado do ADK como o Runner escolhe o agente na retomada, e testar: pedir a confirmação, reiniciar a API e aprovar, com a sessão persistida em Postgres. Se a combinação falhar, registrar a mudança em nova decisão.

> Os detalhes de funcionamento interno do ADK citados aqui precisam ser verificados no código instalado.
