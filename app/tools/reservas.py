"""Tools de reservas. Dados lidos e gravados pelo repositorio, nunca pela memoria do modelo.

As respostas sao genericas de proposito: nunca incluem codigo de reserva nem apartamento
de terceiros, porque tudo o que a tool devolve vira evento da sessao.
"""

from google.adk.tools import FunctionTool, ToolContext

from app.repositorio import RepositorioCondominio
from app.tools._comum import (
    DATA_INVALIDA,
    SEM_SESSAO,
    apartamento_da_sessao,
    interpretar_data,
)


def criar_tools_reservas(repo: RepositorioCondominio) -> list[FunctionTool]:
    async def exige_confirmacao(area: str, data: str, tool_context: ToolContext) -> bool:
        """GARANTIA 1: reservar area com taxa > 0 gera cobranca e fica pendente.

        Decidido pelo codigo, a partir da taxa em dados/areas.json. Area desconhecida
        tambem pede confirmacao (falha fechada).
        """
        info = await repo.obter_area(area)
        return info is None or info["taxa"] > 0

    async def consultar_disponibilidade(area: str, data: str) -> dict:
        """Informa se uma area comum esta livre em uma data (AAAA-MM-DD).

        Args:
            area: id da area (salao-de-festas, churrasqueira ou quadra).
            data: data no formato AAAA-MM-DD.
        """
        d = interpretar_data(data)
        if d is None:
            return DATA_INVALIDA
        if await repo.obter_area(area) is None:
            return {"status": "erro", "mensagem": "Area inexistente."}
        livre = await repo.area_disponivel(area, d)
        return {"status": "livre" if livre else "ocupada", "area": area, "data": data}

    async def reservar_area(area: str, data: str, tool_context: ToolContext) -> dict:
        """Reserva uma area comum para o apartamento do morador em uma data.

        Areas com taxa geram cobranca e exigem confirmacao do morador.

        Args:
            area: id da area (salao-de-festas, churrasqueira ou quadra).
            data: data no formato AAAA-MM-DD.
        """
        apartamento = apartamento_da_sessao(tool_context)
        if apartamento is None:
            return SEM_SESSAO
        d = interpretar_data(data)
        if d is None:
            return DATA_INVALIDA
        r = await repo.reservar(apartamento, area, d)
        if r.status == "criada":
            return {"status": "reservada", "codigo": r.codigo, "area": area, "data": data}
        if r.status == "area_invalida":
            return {"status": "erro", "mensagem": "Area inexistente."}
        return {"status": "indisponivel", "mensagem": "A data nao esta disponivel para esta area."}

    async def cancelar_reserva(area: str, data: str, tool_context: ToolContext) -> dict:
        """Cancela a reserva do proprio apartamento de uma area em uma data.

        Nao exige confirmacao. So age sobre reservas do apartamento da sessao.

        Args:
            area: id da area (salao-de-festas, churrasqueira ou quadra).
            data: data no formato AAAA-MM-DD.
        """
        apartamento = apartamento_da_sessao(tool_context)
        if apartamento is None:
            return SEM_SESSAO
        d = interpretar_data(data)
        if d is None:
            return DATA_INVALIDA
        codigo = await repo.cancelar(apartamento, area, d)
        if codigo is None:
            return {
                "status": "nao_encontrada",
                "mensagem": "Nao ha reserva do seu apartamento para essa area e data.",
            }
        return {"status": "cancelada", "codigo": codigo, "area": area, "data": data}

    async def listar_minhas_reservas(tool_context: ToolContext) -> dict:
        """Lista as reservas ativas do apartamento do morador."""
        apartamento = apartamento_da_sessao(tool_context)
        if apartamento is None:
            return SEM_SESSAO
        return {"status": "ok", "reservas": await repo.reservas_do_apartamento(apartamento)}

    return [
        FunctionTool(consultar_disponibilidade),
        FunctionTool(reservar_area, require_confirmation=exige_confirmacao),
        FunctionTool(cancelar_reserva),
        FunctionTool(listar_minhas_reservas),
    ]
