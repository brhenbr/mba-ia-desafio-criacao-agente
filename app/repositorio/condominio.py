"""Acesso aos dados do condominio (schema `condominio`).

Toda regra de dados critica vive aqui, em SQL, e nao no que o modelo decide:
- exclusividade da reserva: indice unico parcial + INSERT ... ON CONFLICT DO NOTHING;
- cancelamento restrito ao apartamento informado;
- transicao atomica de estado das confirmacoes.

Os metodos recebem o apartamento como parametro, mas quem os chama (as tools) deve
passar sempre o apartamento da sessao, nunca um valor escolhido pelo modelo.
"""

import json
from dataclasses import dataclass
from datetime import date

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine


@dataclass(frozen=True)
class ResultadoReserva:
    # "criada" | "indisponivel" | "area_invalida"
    status: str
    codigo: str | None = None


@dataclass(frozen=True)
class ResultadoVisitante:
    # "autorizado" | "ja_autorizado"
    status: str


class RepositorioCondominio:
    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    # ---------------------------------------------------------------- areas

    async def obter_area(self, area_id: str) -> dict | None:
        async with self._engine.connect() as conn:
            row = (
                (
                    await conn.execute(
                        text("SELECT id, nome, taxa FROM condominio.areas WHERE id = :id"),
                        {"id": area_id},
                    )
                )
                .mappings()
                .first()
            )
        return dict(row) if row else None

    # -------------------------------------------------------------- sessoes

    async def apartamento_existe(self, apartamento: str) -> bool:
        async with self._engine.connect() as conn:
            return (
                await conn.execute(
                    text("SELECT 1 FROM condominio.apartamentos WHERE numero = :n"),
                    {"n": apartamento},
                )
            ).first() is not None

    async def registrar_sessao(self, sessao_id: str, apartamento: str) -> None:
        """Grava o apartamento da sessao. Acontece uma unica vez (ha trigger de imutabilidade)."""
        async with self._engine.begin() as conn:
            await conn.execute(
                text("INSERT INTO condominio.sessoes (id, apartamento) VALUES (:id, :apto)"),
                {"id": sessao_id, "apto": apartamento},
            )

    async def apartamento_da_sessao(self, sessao_id: str) -> str | None:
        async with self._engine.connect() as conn:
            return (
                await conn.execute(
                    text("SELECT apartamento FROM condominio.sessoes WHERE id = :id"),
                    {"id": sessao_id},
                )
            ).scalar()

    # ------------------------------------------------------------- reservas

    async def reservar(self, apartamento: str, area: str, data: date) -> ResultadoReserva:
        """Grava a reserva se a area estiver livre na data.

        Nao ha conferencia previa: o INSERT e atomico e o indice unico parcial
        (area, data) WHERE status = 'ativa' decide quem vence uma disputa.
        """
        if await self.obter_area(area) is None:
            return ResultadoReserva("area_invalida")
        async with self._engine.begin() as conn:
            codigo = (
                await conn.execute(
                    text(
                        """
                        INSERT INTO condominio.reservas (apartamento, area, data)
                        VALUES (:apartamento, :area, :data)
                        ON CONFLICT (area, data) WHERE status = 'ativa' DO NOTHING
                        RETURNING codigo
                        """
                    ),
                    {"apartamento": apartamento, "area": area, "data": data},
                )
            ).scalar()
        if codigo is None:
            return ResultadoReserva("indisponivel")
        return ResultadoReserva("criada", codigo)

    async def cancelar(self, apartamento: str, area: str, data: date) -> str | None:
        """Cancela a reserva ativa DO APARTAMENTO informado. Devolve o codigo ou None."""
        async with self._engine.begin() as conn:
            return (
                await conn.execute(
                    text(
                        """
                        UPDATE condominio.reservas
                           SET status = 'cancelada', cancelada_em = now()
                         WHERE apartamento = :apartamento AND area = :area
                           AND data = :data AND status = 'ativa'
                        RETURNING codigo
                        """
                    ),
                    {"apartamento": apartamento, "area": area, "data": data},
                )
            ).scalar()

    async def reservas_do_apartamento(self, apartamento: str) -> list[dict]:
        async with self._engine.connect() as conn:
            rows = (
                (
                    await conn.execute(
                        text(
                            """
                        SELECT codigo, area, data FROM condominio.reservas
                         WHERE apartamento = :apartamento AND status = 'ativa'
                         ORDER BY data, codigo
                        """
                        ),
                        {"apartamento": apartamento},
                    )
                )
                .mappings()
                .all()
            )
        return [
            {"codigo": r["codigo"], "area": r["area"], "data": r["data"].isoformat()} for r in rows
        ]

    async def area_disponivel(self, area: str, data: date) -> bool:
        """Diz apenas se a data esta livre. Nunca revela de quem e a reserva."""
        async with self._engine.connect() as conn:
            ocupada = (
                await conn.execute(
                    text(
                        "SELECT 1 FROM condominio.reservas"
                        " WHERE area = :area AND data = :data AND status = 'ativa'"
                    ),
                    {"area": area, "data": data},
                )
            ).first()
        return ocupada is None

    # ----------------------------------------------------------- visitantes

    async def autorizar_visitante(
        self, apartamento: str, nome: str, data: date
    ) -> ResultadoVisitante:
        async with self._engine.begin() as conn:
            inserido = (
                await conn.execute(
                    text(
                        """
                        INSERT INTO condominio.visitantes (apartamento, nome, data)
                        VALUES (:apartamento, :nome, :data)
                        ON CONFLICT (apartamento, nome, data) DO NOTHING
                        RETURNING id
                        """
                    ),
                    {"apartamento": apartamento, "nome": nome, "data": data},
                )
            ).scalar()
        return ResultadoVisitante("autorizado" if inserido is not None else "ja_autorizado")

    async def visitantes_do_apartamento(self, apartamento: str) -> list[dict]:
        async with self._engine.connect() as conn:
            rows = (
                (
                    await conn.execute(
                        text(
                            """
                        SELECT nome, data FROM condominio.visitantes
                         WHERE apartamento = :apartamento ORDER BY data, nome
                        """
                        ),
                        {"apartamento": apartamento},
                    )
                )
                .mappings()
                .all()
            )
        return [{"nome": r["nome"], "data": r["data"].isoformat()} for r in rows]

    # --------------------------------------------------------- confirmacoes

    async def registrar_confirmacao(
        self, confirmacao_id: str, sessao_id: str, acao: str, detalhes: dict
    ) -> None:
        async with self._engine.begin() as conn:
            await conn.execute(
                text(
                    """
                    INSERT INTO condominio.confirmacoes (id, sessao_id, acao, detalhes)
                    VALUES (:id, :sessao_id, :acao, CAST(:detalhes AS jsonb))
                    ON CONFLICT (id) DO NOTHING
                    """
                ),
                {
                    "id": confirmacao_id,
                    "sessao_id": sessao_id,
                    "acao": acao,
                    "detalhes": json.dumps(detalhes),
                },
            )

    async def confirmacoes_pendentes(self, sessao_id: str) -> list[dict]:
        async with self._engine.connect() as conn:
            rows = (
                (
                    await conn.execute(
                        text(
                            """
                        SELECT id, acao, detalhes FROM condominio.confirmacoes
                         WHERE sessao_id = :sessao_id AND estado = 'pendente'
                         ORDER BY criada_em, id
                        """
                        ),
                        {"sessao_id": sessao_id},
                    )
                )
                .mappings()
                .all()
            )
        return [
            {
                "id": r["id"],
                "acao": r["acao"],
                "detalhes": json.loads(r["detalhes"])
                if isinstance(r["detalhes"], str)
                else r["detalhes"],
            }
            for r in rows
        ]

    async def responder_confirmacao(
        self, confirmacao_id: str, sessao_id: str, confirmado: bool
    ) -> bool:
        """Transicao atomica pendente -> aprovada/negada.

        Devolve True so para quem venceu a transicao. Um id inexistente, de outra sessao
        ou ja respondido nao muda nenhuma linha e devolve False (a API responde 409).
        """
        async with self._engine.begin() as conn:
            mudou = (
                await conn.execute(
                    text(
                        """
                        UPDATE condominio.confirmacoes
                           SET estado = :estado, respondida_em = now()
                         WHERE id = :id AND sessao_id = :sessao_id AND estado = 'pendente'
                        RETURNING id
                        """
                    ),
                    {
                        "id": confirmacao_id,
                        "sessao_id": sessao_id,
                        "estado": "aprovada" if confirmado else "negada",
                    },
                )
            ).scalar()
        return mudou is not None
