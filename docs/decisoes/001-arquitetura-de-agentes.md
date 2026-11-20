# 001. Arquitetura de agentes

- **Status:** aceita provisoriamente (a validar quando testarmos a retomada de confirmações com sessão persistida)
- **Data:** 2026-11-20

## Contexto

O enunciado exige um agente principal e no mínimo dois especialistas, e deixa livres quantos criar, o que cada um faz e como são acionados. A Garantia 1 (confirmação de ações) depende de a resposta do morador chegar ao agente que pediu a confirmação, e o enunciado avisa que isso varia com a topologia dos agentes.

## Alternativas consideradas

1. **Principal + 2 especialistas** (por exemplo, "reservas e visitantes" juntos, e "regulamento"). Simples, mas mistura dois domínios com regras de confirmação diferentes.
2. **Principal + 3 especialistas por domínio**: reservas, visitantes e regulamento.
3. **Um agente por ação** (reservar, cancelar, checar agenda, autorizar visitante, etc.). Mais granular, porém cada transferência custa uma chamada ao modelo, aumenta o risco de roteamento errado e multiplica os caminhos de retomada da confirmação.

## Decisão

Opção 2. O agente principal só conversa e roteia. Ele não tem tools de dados.

| Agente | Responsabilidade |
|---|---|
| principal | Entender o pedido e delegar ao especialista certo |
| reservas | Reservar, cancelar, listar reservas, consultar disponibilidade |
| visitantes | Autorizar e listar visitantes |
| regulamento | Responder dúvidas consultando o regulamento por trecho |

## Consequências

- Cada especialista tem tools e instruções curtas e focadas.
- As regras críticas (apartamento da sessão, confirmação, exclusividade) ficam no código das tools, não nas instruções dos agentes.
- O regulamento fica isolado no especialista de regulamento, o que ajuda a Garantia 4.
- O mecanismo de acionamento (sub_agents ou AgentTool) ainda será decidido em registro próprio, depois de testar a retomada de confirmação.
