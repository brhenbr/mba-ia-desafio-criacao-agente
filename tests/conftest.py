"""Fixtures: um banco PostgreSQL de teste (aurora_test), restaurado a cada teste.

Requer o Postgres do docker-compose no ar (`docker compose up -d`).
"""

import asyncio

import asyncpg
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine

from app.config import get_settings
from app.repositorio import RepositorioCondominio
from scripts.restaurar import restaurar

BANCO_TESTE = "aurora_test"


def _url_teste() -> str:
    s = get_settings()
    return (
        f"postgresql+asyncpg://{s.postgres_user}:{s.postgres_password}"
        f"@{s.postgres_host}:{s.postgres_port}/{BANCO_TESTE}"
    )


@pytest.fixture(scope="session")
def url_teste() -> str:
    async def criar_banco() -> None:
        s = get_settings()
        conn = await asyncpg.connect(
            user=s.postgres_user,
            password=s.postgres_password,
            host=s.postgres_host,
            port=s.postgres_port,
            database=s.postgres_db,
        )
        existe = await conn.fetchval("SELECT 1 FROM pg_database WHERE datname = $1", BANCO_TESTE)
        if not existe:
            await conn.execute(f"CREATE DATABASE {BANCO_TESTE}")
        await conn.close()

    asyncio.run(criar_banco())
    return _url_teste()


@pytest_asyncio.fixture
async def repo(url_teste: str):
    # restaurar() e sincrona (o Alembic cria o proprio loop), entao roda em outra thread.
    await asyncio.to_thread(restaurar, url_teste)
    engine = create_async_engine(url_teste, pool_size=20)
    yield RepositorioCondominio(engine)
    await engine.dispose()
