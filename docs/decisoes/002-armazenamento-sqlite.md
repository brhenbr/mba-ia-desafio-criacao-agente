# 002. Armazenamento: SQLite

- **Status:** substituída pela [003](003-armazenamento-postgres.md)
- **Data:** 2026-11-20

## Contexto

Precisamos guardar os dados do condomínio (reservas e visitantes) e as sessões do ADK, com persistência no reinício (Garantia 3) e exclusividade de reserva no instante da gravação (Garantia 5).

## Decisão original

SQLite, com `DatabaseSessionService` do ADK, índice único parcial `UNIQUE(area, data)` para reservas ativas, cancelamento lógico, modo WAL e `busy_timeout`.

## Por que foi substituída

Ao definirmos que o projeto deve ser sustentável e pronto para produção com escala moderada, as limitações do SQLite pesaram:
- um escritor por vez (cada evento de conversa disputa o lock com as reservas);
- adequado a uma única instância da API;
- dados e sessões no mesmo arquivo ou em arquivos separados, sem um backup único.

As vantagens (zero infraestrutura) eram sobretudo de conveniência para o avaliador, e o enunciado permite um serviço externo com comando documentado.

## O que continua valendo

- Exclusividade por índice único parcial, e não por conferência prévia.
- Cancelamento lógico, para nunca reutilizar o código de uma reserva cancelada.
- SQLite continua como plano de contingência caso o spike da decisão 003 falhe.
