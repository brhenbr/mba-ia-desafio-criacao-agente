"""Carga do estado inicial do condominio a partir de dados/*.json."""

import json
from datetime import date
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

DADOS = Path(__file__).resolve().parents[2] / "dados"


def _ler(nome: str) -> list[dict]:
    return json.loads((DADOS / nome).read_text(encoding="utf-8"))


async def carregar_dados_iniciais(engine: AsyncEngine) -> None:
    async with engine.begin() as conn:
        for a in _ler("apartamentos.json"):
            await conn.execute(
                text("INSERT INTO condominio.apartamentos (numero, morador) VALUES (:n, :m)"),
                {"n": a["numero"], "m": a["morador"]},
            )
        for a in _ler("areas.json"):
            await conn.execute(
                text("INSERT INTO condominio.areas (id, nome, taxa) VALUES (:id, :nome, :taxa)"),
                {"id": a["id"], "nome": a["nome"], "taxa": a["taxa"]},
            )
        for r in _ler("reservas.json"):
            await conn.execute(
                text(
                    "INSERT INTO condominio.reservas (codigo, apartamento, area, data)"
                    " VALUES (:codigo, :apartamento, :area, :data)"
                ),
                {**r, "data": date.fromisoformat(r["data"])},
            )
        for v in _ler("visitantes.json"):
            await conn.execute(
                text(
                    "INSERT INTO condominio.visitantes (apartamento, nome, data)"
                    " VALUES (:apartamento, :nome, :data)"
                ),
                {**v, "data": date.fromisoformat(v["data"])},
            )
