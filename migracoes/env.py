"""Ambiente do Alembic para o schema `condominio` (execucao assincrona)."""

import asyncio

from alembic import context
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool

from app.config import get_settings

config = context.config
SCHEMA = "condominio"


def _url() -> str:
    # Permite que testes e scripts apontem para outro banco.
    return config.attributes.get("url") or get_settings().database_url


def _migrar(connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=None,
        version_table_schema=SCHEMA,
    )
    with context.begin_transaction():
        context.run_migrations()


async def _executar() -> None:
    engine = create_async_engine(_url(), poolclass=NullPool)
    async with engine.connect() as conn:
        # O schema precisa existir antes de o Alembic criar a tabela de versao nele.
        await conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {SCHEMA}"))
        await conn.commit()
        await conn.run_sync(_migrar)
    await engine.dispose()


asyncio.run(_executar())
