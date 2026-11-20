"""Restaura o estado inicial do condominio (reset COMPLETO).

Apaga os schemas `condominio` e `sessoes`, recria o esquema por migracoes e carrega
dados/*.json. Reservas, visitantes, confirmacoes e sessoes voltam ao zero.

Uso: uv run python -m scripts.restaurar --sim
"""

import argparse
import asyncio
import sys

from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool

from app.config import get_settings
from app.repositorio.seed import carregar_dados_iniciais


async def _recriar_schemas(url: str) -> None:
    engine = create_async_engine(url, poolclass=NullPool)
    async with engine.begin() as conn:
        await conn.execute(text("DROP SCHEMA IF EXISTS condominio CASCADE"))
        await conn.execute(text("DROP SCHEMA IF EXISTS sessoes CASCADE"))
        await conn.execute(text("CREATE SCHEMA sessoes"))
    await engine.dispose()


async def _seed(url: str) -> None:
    engine = create_async_engine(url, poolclass=NullPool)
    await carregar_dados_iniciais(engine)
    await engine.dispose()


def restaurar(url: str) -> None:
    """Recria tudo no banco indicado. Sincrona: o Alembic gerencia o proprio event loop."""
    asyncio.run(_recriar_schemas(url))
    cfg = Config("alembic.ini")
    cfg.attributes["url"] = url
    command.upgrade(cfg, "head")
    asyncio.run(_seed(url))


def main() -> int:
    parser = argparse.ArgumentParser(description="Restaura o estado inicial (apaga tudo).")
    parser.add_argument("--sim", action="store_true", help="confirma que quer apagar tudo")
    args = parser.parse_args()

    settings = get_settings()
    if settings.producao:
        print("Recusado: AMBIENTE indica producao. A restauracao apaga todos os dados.")
        return 1
    if not args.sim:
        print("Isto apaga reservas, visitantes e sessoes. Rode de novo com --sim para confirmar.")
        return 1

    restaurar(settings.database_url)
    print("Estado inicial restaurado.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
