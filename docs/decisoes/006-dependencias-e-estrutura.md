# 006. Dependências, migrações e estrutura do projeto

- **Status:** aceita (versão do ADK pendente)
- **Data:** 2026-11-20

## Decisões

- **Gerenciador:** `uv`, com `pyproject.toml` e `uv.lock` versionados.
- **Python:** 3.12 fixado, o mínimo exigido pelo enunciado, para o ambiente do avaliador ser igual ao nosso.
- **Dependências de runtime:** `google-adk` (versão exata fixada), `fastapi`, `uvicorn`, `sqlalchemy` com driver assíncrono do Postgres, `alembic` e `pydantic-settings` (lê o `.env`).
- **Qualidade:** `ruff` (lint e formatação) e `pytest` (com `pytest-asyncio`) desde o início, em grupo de dependências de desenvolvimento.
- **Migrações do schema `condominio`:** Alembic. O schema de sessões é gerenciado pelo próprio ADK.

### Por que Alembic e não SQL simples

| | Alembic | SQL de inicialização |
|---|---|---|
| Histórico de mudanças do esquema | versionado, com subida e descida | não há |
| Evolução em produção | padrão da indústria | exige criar um mecanismo próprio |
| Custo inicial | maior (configuração assíncrona, uma pasta de migrações) | quase zero |
| Risco para o desafio | baixo, mas é mais uma peça | baixo |

Como o objetivo é um projeto sustentável, escolhemos Alembic: o esquema deixa de ser um script solto e passa a ter versão.

## Estrutura

```
app/
  main.py          # FastAPI e rotas
  config.py        # leitura do .env
  agentes/         # principal e especialistas
  tools/           # regras críticas das garantias
  repositorio/     # acesso ao banco
  regulamento/     # índice e busca no regulamento
migracoes/         # Alembic
scripts/           # restauração dos dados
tests/
docs/decisoes/
docker-compose.yml
.env.example
```

## Versão do ADK

Fixada em **2.9.1** (`google-adk==2.9.1`). O enunciado exige a série 2, a partir da 2.2.0, e informa que a 2.2.0 e a 2.9.1 foram testadas pelos autores. Escolhemos a 2.9.1 por ser validada e mais recente que a do curso. A 2.15.0 (a mais nova no PyPI) não foi validada. O spike também testará a 2.2.0; se alguma falhar, a troca é feita em um único lugar (`pyproject.toml`).

Python fixado em `>=3.12,<3.13`.

## Comandos do README

- `docker compose up -d`: sobe o banco.
- `uv sync`: instala.
- `uv run python -m scripts.restaurar --sim`: restaura os dados.
- `uv run uvicorn app.main:app --port 8000`: sobe a API.
