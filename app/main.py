"""API HTTP do assistente do Residencial Aurora (contrato do enunciado)."""

import asyncio
from contextlib import asynccontextmanager

from alembic import command
from alembic.config import Config
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from google.adk.runners import Runner
from google.adk.sessions import DatabaseSessionService
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.agentes.montagem import criar_app
from app.config import get_settings
from app.repositorio import RepositorioCondominio
from app.servico import ConfirmacaoNaoPendente, ErroDeExecucao, ServicoConversa


class NovaSessao(BaseModel):
    apartamento: str


class NovaMensagem(BaseModel):
    texto: str


class RespostaConfirmacao(BaseModel):
    id: str
    confirmado: bool


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    # Garante o esquema do condominio na versao atual (idempotente).
    await asyncio.to_thread(command.upgrade, Config("alembic.ini"), "head")
    engine = create_async_engine(settings.database_url, pool_size=20, max_overflow=20)
    async with engine.begin() as conn:
        await conn.execute(text("CREATE SCHEMA IF NOT EXISTS sessoes"))
    repo = RepositorioCondominio(engine)
    # Sessoes do ADK no schema proprio `sessoes`; sobrevivem ao reinicio (Garantia 3).
    sessoes = DatabaseSessionService(
        settings.database_url, connect_args={"server_settings": {"search_path": "sessoes"}}
    )
    runner = Runner(app=criar_app(repo, settings), session_service=sessoes)
    app.state.repo = repo
    app.state.servico = ServicoConversa(runner, sessoes, repo)
    yield
    await engine.dispose()


app = FastAPI(title="Assistente do Residencial Aurora", lifespan=lifespan)


async def _exigir_sessao(servico: ServicoConversa, sessao_id: str) -> None:
    if not await servico.sessao_existe(sessao_id):
        raise HTTPException(status_code=404, detail="Sessao nao encontrada.")


@app.exception_handler(ErroDeExecucao)
async def _erro_de_execucao(_, __):
    return JSONResponse(status_code=500, content={"detail": "Erro ao processar a solicitacao."})


@app.post("/sessoes", status_code=201)
async def criar_sessao(corpo: NovaSessao):
    sessao_id = await app.state.servico.criar_sessao(corpo.apartamento)
    if sessao_id is None:
        raise HTTPException(status_code=404, detail="Apartamento nao encontrado.")
    return {"session_id": sessao_id}


@app.post("/sessoes/{session_id}/mensagens")
async def enviar_mensagem(session_id: str, corpo: NovaMensagem):
    await _exigir_sessao(app.state.servico, session_id)
    return await app.state.servico.enviar_mensagem(session_id, corpo.texto)


@app.post("/sessoes/{session_id}/confirmacoes")
async def responder_confirmacao(session_id: str, corpo: RespostaConfirmacao):
    await _exigir_sessao(app.state.servico, session_id)
    try:
        return await app.state.servico.responder_confirmacao(session_id, corpo.id, corpo.confirmado)
    except ConfirmacaoNaoPendente:
        raise HTTPException(
            status_code=409, detail="Nao existe confirmacao pendente com esse id nesta sessao."
        ) from None


@app.get("/sessoes/{session_id}/eventos")
async def listar_eventos(session_id: str):
    await _exigir_sessao(app.state.servico, session_id)
    return await app.state.servico.eventos(session_id)


# Rotas de verificacao: leem o banco direto, sem passar pelo modelo.
# Em producao ficariam atras de acesso administrativo.
@app.get("/apartamentos/{numero}/reservas")
async def reservas_do_apartamento(numero: str):
    return await app.state.repo.reservas_do_apartamento(numero)


@app.get("/apartamentos/{numero}/visitantes")
async def visitantes_do_apartamento(numero: str):
    return await app.state.repo.visitantes_do_apartamento(numero)
