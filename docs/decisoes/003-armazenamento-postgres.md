# 003. Armazenamento: PostgreSQL com dois schemas e reset completo

- **Status:** aceita, condicionada ao spike descrito abaixo
- **Data:** 2026-11-20
- **Substitui:** [002](002-armazenamento-sqlite.md)

## Contexto

O projeto deve ser sustentável e pronto para um ambiente produtivo com escala moderada. Precisamos de persistência no reinício (Garantia 3) e de exclusividade de reserva sob concorrência (Garantia 5). O enunciado permite um serviço externo desde que suba com um comando documentado.

## Alternativas consideradas

| Opção | Motivo de não escolher |
|---|---|
| SQLite (002) | Um escritor por vez, uma única instância, sem backup único |
| JSON + lock | Exclusividade por lock e não pelo banco; escrita não atômica; persistência de sessão parcial |

## Decisão

**PostgreSQL** em container (`docker compose`), com **um servidor e dois schemas**:

- `condominio`: reservas e visitantes, lidos e gravados pelas tools.
- `sessoes`: tabelas do `DatabaseSessionService` do ADK.

Pontos de projeto:
- **Exclusividade:** índice único parcial em reservas ativas, por área e data. A gravação usa `INSERT ... ON CONFLICT DO NOTHING`, e a ausência de linha inserida vira uma recusa normal, sem erro de servidor.
- **Cancelamento lógico**, para nunca reutilizar o código de uma reserva cancelada. O código vem de uma sequência do banco.
- **Camada de repositório:** as tools não falam SQL. O acesso aos dados fica atrás de uma interface, o que isola o banco e facilita testes e trocas futuras.
- **Subida:** `docker compose up -d` com healthcheck. O comando de subida da API aguarda o banco ficar pronto.

### Política de restauração

A restauração é um **reset completo** para o estado inicial: recria os dados do condomínio a partir de `dados/*.json` e apaga as sessões. Não existe modo de preservar sessões, porque conversas apontando para dados que já não existem seriam um estado inconsistente.

Como a ferramenta é destrutiva:
- exige confirmação explícita (`--sim` ou pergunta interativa);
- se recusa a rodar quando uma variável de ambiente indicar produção.

Em produção, o estado evolui por migrações de esquema, nunca por restauração.

## Spike obrigatório (primeira tarefa de implementação)

Antes de construir qualquer outra coisa, validar que a confirmação de ação funciona com o `DatabaseSessionService` sobre Postgres: pedir uma confirmação, reiniciar o processo e aprovar. O enunciado só atesta que isso funcionou com SQLite.

**Se falhar:** voltar ao SQLite (002), mantendo a camada de repositório, e registrar a mudança em nova decisão.

## Consequências

- O avaliador precisa de Docker e de uma porta livre (5432). O README documenta isso.
- Concorrência real nas aprovações simultâneas, com um backup único.
- O código de dados depende da camada de repositório e do driver assíncrono do Postgres.
