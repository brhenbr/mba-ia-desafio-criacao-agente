"""Servico de conversa: liga a API ao Runner do ADK e as confirmacoes ao banco.

Fluxo das confirmacoes (decisoes 005 e 007):
1. O ADK pausa a tool e emite uma chamada `adk_request_confirmation`.
2. Registramos essa confirmacao como `pendente` em condominio.confirmacoes.
3. A rota de confirmacoes so repassa a resposta ao ADK para quem vence a transicao
   atomica pendente -> aprovada/negada. O resto recebe 409 e nada chega ao ADK.
"""

import asyncio
import logging
from collections import defaultdict

from google.adk.runners import Runner
from google.adk.sessions import DatabaseSessionService
from google.genai import types

from app.agentes.montagem import NOME_APP
from app.repositorio import RepositorioCondominio

log = logging.getLogger("aurora.servico")

PEDIDO_CONFIRMACAO = "adk_request_confirmation"
CHAVE_APARTAMENTO = "apartamento"


class ConfirmacaoNaoPendente(Exception):
    """O id nao esta pendente nesta sessao (inexistente, ja respondido ou de outra sessao)."""


class ErroDeExecucao(Exception):
    """O Runner falhou ao processar a mensagem ou ao retomar a confirmacao."""


class ServicoConversa:
    def __init__(
        self, runner: Runner, sessoes: DatabaseSessionService, repo: RepositorioCondominio
    ) -> None:
        self._runner = runner
        self._sessoes = sessoes
        self._repo = repo
        # Uma execucao por vez em cada sessao (neste processo).
        self._travas: defaultdict[str, asyncio.Lock] = defaultdict(asyncio.Lock)

    # -------------------------------------------------------------- sessoes

    async def criar_sessao(self, apartamento: str) -> str | None:
        """Cria a sessao do apartamento. O apartamento so e definido aqui, uma unica vez."""
        if not await self._repo.apartamento_existe(apartamento):
            return None
        sessao = await self._sessoes.create_session(
            app_name=NOME_APP, user_id=apartamento, state={CHAVE_APARTAMENTO: apartamento}
        )
        await self._repo.registrar_sessao(sessao.id, apartamento)
        return sessao.id

    async def sessao_existe(self, sessao_id: str) -> bool:
        return await self._repo.apartamento_da_sessao(sessao_id) is not None

    async def eventos(self, sessao_id: str) -> list[dict]:
        apartamento = await self._repo.apartamento_da_sessao(sessao_id)
        sessao = await self._sessoes.get_session(
            app_name=NOME_APP, user_id=apartamento, session_id=sessao_id
        )
        return [e.model_dump(mode="json", exclude_none=True) for e in sessao.events]

    # ------------------------------------------------------------ conversa

    async def enviar_mensagem(self, sessao_id: str, texto: str) -> dict:
        conteudo = types.Content(role="user", parts=[types.Part(text=texto)])
        async with self._travas[sessao_id]:
            return await self._executar(sessao_id, conteudo)

    async def responder_confirmacao(
        self, sessao_id: str, confirmacao_id: str, confirmado: bool
    ) -> dict:
        async with self._travas[sessao_id]:
            # So quem vence a transicao atomica fala com o ADK.
            if not await self._repo.responder_confirmacao(confirmacao_id, sessao_id, confirmado):
                raise ConfirmacaoNaoPendente(confirmacao_id)
            conteudo = types.Content(
                role="user",
                parts=[
                    types.Part(
                        function_response=types.FunctionResponse(
                            id=confirmacao_id,
                            name=PEDIDO_CONFIRMACAO,
                            response={"confirmed": confirmado},
                        )
                    )
                ],
            )
            # Se a execucao falhar daqui em diante, a confirmacao continua respondida:
            # preferimos "no maximo uma vez" a arriscar executar duas (decisao 007).
            return await self._executar(sessao_id, conteudo)

    async def _executar(self, sessao_id: str, conteudo: types.Content) -> dict:
        apartamento = await self._repo.apartamento_da_sessao(sessao_id)
        textos: list[str] = []
        try:
            async for evento in self._runner.run_async(
                user_id=apartamento, session_id=sessao_id, new_message=conteudo
            ):
                for chamada in evento.get_function_calls():
                    if chamada.name == PEDIDO_CONFIRMACAO:
                        await self._registrar_pendente(sessao_id, chamada)
                if evento.author != "user" and evento.content and evento.content.parts:
                    textos += [p.text for p in evento.content.parts if p.text and not p.thought]
        except Exception as erro:
            log.exception("falha ao executar a sessao %s", sessao_id)
            raise ErroDeExecucao(str(erro)) from erro
        return {
            "resposta": "\n".join(textos).strip(),
            "confirmacoes_pendentes": await self._repo.confirmacoes_pendentes(sessao_id),
        }

    async def _registrar_pendente(self, sessao_id: str, chamada: types.FunctionCall) -> None:
        original = (chamada.args or {}).get("originalFunctionCall", {})
        acao = original.get("name", "acao")
        detalhes = dict(original.get("args") or {})
        if acao == "reservar_area":
            area = await self._repo.obter_area(detalhes.get("area", ""))
            if area is not None:
                detalhes["taxa"] = float(area["taxa"])
        await self._repo.registrar_confirmacao(chamada.id, sessao_id, acao, detalhes)
