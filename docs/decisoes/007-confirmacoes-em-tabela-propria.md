# 007. Confirmações pendentes em tabela própria

- **Status:** aceita
- **Data:** 2026-11-20

## Contexto

No spike (ver [005](005-acionamento-dos-especialistas.md)) constatamos que o ADK, ao receber uma resposta de confirmação, executa a ação mesmo quando essa confirmação já foi respondida: uma confirmação negada e depois reenviada com `confirmed: true` executou a tool. O contrato exige `409` para um `id` que não esteja pendente na sessão (inclusive um já respondido), e que aprovar execute a ação uma única vez, mesmo com duas respostas simultâneas.

## Alternativas

| Opção | Prós | Contras |
|---|---|---|
| A. Calcular as pendentes pelos eventos da sessão (chamadas `adk_request_confirmation` sem resposta) | Fonte única da verdade, já persistida | Lê todos os eventos a cada chamada; duas respostas simultâneas ao mesmo `id` podem passar juntas |
| B. Tabela própria de confirmações com transição atômica de estado | `409` e "uma única vez" garantidos pelo banco, inclusive em corrida | Mais uma tabela para manter coerente com os eventos |

## Decisão

**Opção B.** O schema `condominio` terá uma tabela de confirmações com `id` (o da chamada `adk_request_confirmation`), a sessão, a ação, os detalhes e o estado (`pendente`, `aprovada`, `negada`).

- Quando a execução pausa e o ADK emite o pedido de confirmação, a API registra a confirmação como `pendente`.
- Ao receber uma resposta, a API faz uma transição atômica (`UPDATE ... SET estado = ... WHERE id = ? AND sessao = ? AND estado = 'pendente'`). Se nenhuma linha mudar, responde `409` e **não** envia nada ao ADK.
- Só a requisição que vence a transição repassa a resposta ao Runner.
- `confirmacoes_pendentes` na resposta da API vem desta tabela, filtrada pela sessão.

## Consequências

- A garantia não depende do ADK nem do modelo, e é o mesmo princípio da exclusividade de reserva: a regra vale no instante da gravação.
- Precisamos manter a tabela coerente com a execução do ADK. Se o envio ao Runner falhar depois da transição, é preciso um tratamento definido (a definir na implementação).
