"""Tools de visitantes. Autorizar libera acesso ao predio, entao SEMPRE exige confirmacao."""

from google.adk.tools import FunctionTool, ToolContext

from app.repositorio import RepositorioCondominio
from app.tools._comum import (
    DATA_INVALIDA,
    SEM_SESSAO,
    apartamento_da_sessao,
    interpretar_data,
)


def criar_tools_visitantes(repo: RepositorioCondominio) -> list[FunctionTool]:
    async def autorizar_visitante(nome: str, data: str, tool_context: ToolContext) -> dict:
        """Autoriza a entrada de um visitante no predio em uma data.

        Libera acesso, entao exige confirmacao do morador pelo sistema.

        Args:
            nome: nome completo do visitante.
            data: data da visita no formato AAAA-MM-DD.
        """
        apartamento = apartamento_da_sessao(tool_context)
        if apartamento is None:
            return SEM_SESSAO
        d = interpretar_data(data)
        if d is None:
            return DATA_INVALIDA
        nome = nome.strip()
        if not nome:
            return {"status": "erro", "mensagem": "Informe o nome do visitante."}
        r = await repo.autorizar_visitante(apartamento, nome, d)
        return {"status": r.status, "nome": nome, "data": data}

    async def listar_meus_visitantes(tool_context: ToolContext) -> dict:
        """Lista as visitas autorizadas do apartamento do morador."""
        apartamento = apartamento_da_sessao(tool_context)
        if apartamento is None:
            return SEM_SESSAO
        return {"status": "ok", "visitantes": await repo.visitantes_do_apartamento(apartamento)}

    return [
        FunctionTool(autorizar_visitante, require_confirmation=True),
        FunctionTool(listar_meus_visitantes),
    ]
