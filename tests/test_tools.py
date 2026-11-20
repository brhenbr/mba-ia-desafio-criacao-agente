"""Testes das tools sem chamar o modelo: as regras vivem no codigo."""

import inspect
import json
from datetime import date
from types import SimpleNamespace

import pytest

from app.repositorio import RepositorioCondominio
from app.tools.reservas import criar_tools_reservas
from app.tools.visitantes import criar_tools_visitantes


def contexto(apartamento="101", confirmado: bool | None = None):
    """Contexto falso: state da sessao e (opcionalmente) uma resposta de confirmacao."""
    confirmacao = None if confirmado is None else SimpleNamespace(confirmed=confirmado)
    ctx = SimpleNamespace(
        state={"apartamento": apartamento},
        tool_confirmation=confirmacao,
        actions=SimpleNamespace(skip_summarization=False),
        pedidos=0,
    )

    def request_confirmation(**_):
        ctx.pedidos += 1

    ctx.request_confirmation = request_confirmation
    return ctx


@pytest.fixture
def tools(repo: RepositorioCondominio):
    todas = criar_tools_reservas(repo) + criar_tools_visitantes(repo)
    return {t.name: t for t in todas}


async def rodar(tools, nome, args, ctx):
    return await tools[nome].run_async(args=args, tool_context=ctx)


async def test_nenhuma_tool_aceita_apartamento_como_parametro(tools):
    for nome, tool in tools.items():
        assert "apartamento" not in inspect.signature(tool.func).parameters, nome


async def test_area_com_taxa_exige_confirmacao_e_nada_e_gravado_antes(tools, repo):
    ctx = contexto()
    r = await rodar(tools, "reservar_area", {"area": "salao-de-festas", "data": "2030-04-20"}, ctx)
    assert "confirmation" in json.dumps(r) and ctx.pedidos == 1
    assert await repo.area_disponivel("salao-de-festas", date(2030, 4, 20))


async def test_confirmacao_negada_nao_grava(tools, repo):
    ctx = contexto(confirmado=False)
    r = await rodar(tools, "reservar_area", {"area": "salao-de-festas", "data": "2030-04-20"}, ctx)
    assert "rejected" in json.dumps(r)
    assert await repo.area_disponivel("salao-de-festas", date(2030, 4, 20))


async def test_confirmacao_aprovada_grava_uma_reserva(tools, repo):
    ctx = contexto(confirmado=True)
    r = await rodar(tools, "reservar_area", {"area": "salao-de-festas", "data": "2030-04-20"}, ctx)
    assert r["status"] == "reservada"
    assert len(await repo.reservas_do_apartamento("101")) == 2


async def test_area_sem_taxa_nao_pede_confirmacao(tools, repo):
    ctx = contexto()
    r = await rodar(tools, "reservar_area", {"area": "quadra", "data": "2030-04-06"}, ctx)
    assert r["status"] == "reservada" and ctx.pedidos == 0


async def test_visitante_sempre_exige_confirmacao(tools, repo):
    ctx = contexto()
    await rodar(tools, "autorizar_visitante", {"nome": "Joana Ribeiro", "data": "2030-04-21"}, ctx)
    assert ctx.pedidos == 1
    assert await repo.visitantes_do_apartamento("101") == []
    ctx = contexto(confirmado=True)
    r = await rodar(
        tools, "autorizar_visitante", {"nome": "Joana Ribeiro", "data": "2030-04-21"}, ctx
    )
    assert r["status"] == "autorizado"
    assert await repo.visitantes_do_apartamento("101") == [
        {"nome": "Joana Ribeiro", "data": "2030-04-21"}
    ]


async def test_cancelar_reserva_de_outro_apartamento_nao_altera_nem_vaza(tools, repo):
    r = await rodar(
        tools,
        "cancelar_reserva",
        {"area": "salao-de-festas", "data": "2030-03-16"},
        contexto("101"),
    )
    assert r["status"] == "nao_encontrada"
    assert "RSV-4821" not in json.dumps(r) and "302" not in json.dumps(r)
    assert not await repo.area_disponivel("salao-de-festas", date(2030, 3, 16))


async def test_cancelar_a_propria_reserva_sem_confirmacao(tools, repo):
    ctx = contexto("101")
    r = await rodar(tools, "cancelar_reserva", {"area": "quadra", "data": "2030-03-09"}, ctx)
    assert r["status"] == "cancelada" and ctx.pedidos == 0
    assert await repo.reservas_do_apartamento("101") == []


async def test_reservar_data_ocupada_por_outro_nao_vaza(tools, repo):
    ctx = contexto("101", confirmado=True)
    r = await rodar(tools, "reservar_area", {"area": "salao-de-festas", "data": "2030-03-16"}, ctx)
    assert r["status"] == "indisponivel"
    texto = json.dumps(r)
    assert "RSV-4821" not in texto and "302" not in texto
    d = await rodar(
        tools, "consultar_disponibilidade", {"area": "salao-de-festas", "data": "2030-03-16"}, ctx
    )
    assert d["status"] == "ocupada" and "RSV-4821" not in json.dumps(d)


async def test_listagens_so_do_proprio_apartamento(tools):
    r = await rodar(tools, "listar_minhas_reservas", {}, contexto("101"))
    assert [x["codigo"] for x in r["reservas"]] == ["RSV-1377"]
    v = await rodar(tools, "listar_meus_visitantes", {}, contexto("101"))
    assert v["visitantes"] == []  # Marina Duarte e do 302


async def test_data_invalida(tools):
    r = await rodar(
        tools, "consultar_disponibilidade", {"area": "quadra", "data": "amanha"}, contexto()
    )
    assert r["status"] == "erro"
