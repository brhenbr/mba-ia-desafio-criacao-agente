import asyncio
from datetime import date

from app.repositorio import RepositorioCondominio

D = date(2030, 5, 11)


async def test_estado_inicial_restaurado(repo: RepositorioCondominio):
    assert await repo.reservas_do_apartamento("101") == [
        {"codigo": "RSV-1377", "area": "quadra", "data": "2030-03-09"}
    ]
    assert await repo.visitantes_do_apartamento("302") == [
        {"nome": "Marina Duarte", "data": "2030-03-16"}
    ]


async def test_reserva_ocupada_e_recusada_sem_erro(repo: RepositorioCondominio):
    r = await repo.reservar("101", "salao-de-festas", date(2030, 3, 16))  # ocupada pelo 302
    assert r.status == "indisponivel" and r.codigo is None
    assert await repo.area_disponivel("salao-de-festas", date(2030, 3, 16)) is False


async def test_area_invalida(repo: RepositorioCondominio):
    assert (await repo.reservar("101", "piscina", D)).status == "area_invalida"


async def test_garantia5_duas_reservas_simultaneas_so_uma_vence(repo: RepositorioCondominio):
    apartamentos = ["101", "102", "201", "202", "301", "302"] * 4  # 24 disputantes
    resultados = await asyncio.gather(
        *(repo.reservar(a, "salao-de-festas", D) for a in apartamentos)
    )
    assert sum(r.status == "criada" for r in resultados) == 1
    assert sum(r.status == "indisponivel" for r in resultados) == len(apartamentos) - 1
    total = 0
    for a in ("101", "102", "201", "202", "301", "302"):
        reservas = await repo.reservas_do_apartamento(a)
        total += len([x for x in reservas if x["data"] == D.isoformat()])
    assert total == 1


async def test_cancelar_so_o_proprio_apartamento(repo: RepositorioCondominio):
    # O 101 tenta cancelar a reserva do 302: nada muda.
    assert await repo.cancelar("101", "salao-de-festas", date(2030, 3, 16)) is None
    assert not await repo.area_disponivel("salao-de-festas", date(2030, 3, 16))
    # O dono cancela.
    assert await repo.cancelar("302", "salao-de-festas", date(2030, 3, 16)) == "RSV-4821"
    assert await repo.area_disponivel("salao-de-festas", date(2030, 3, 16))


async def test_codigo_nunca_repete_nem_apos_cancelamento(repo: RepositorioCondominio):
    r1 = await repo.reservar("101", "salao-de-festas", D)
    assert await repo.cancelar("101", "salao-de-festas", D) == r1.codigo
    r2 = await repo.reservar("101", "salao-de-festas", D)  # mesma area/data, apos cancelar
    assert r2.status == "criada" and r2.codigo != r1.codigo
    assert r1.codigo not in {"RSV-1377", "RSV-4821", "RSV-2950"}


async def test_autorizar_visitante_e_idempotente(repo: RepositorioCondominio):
    assert (
        await repo.autorizar_visitante("101", "Joana Ribeiro", date(2030, 4, 21))
    ).status == "autorizado"
    assert (
        await repo.autorizar_visitante("101", "Joana Ribeiro", date(2030, 4, 21))
    ).status == "ja_autorizado"
    assert await repo.visitantes_do_apartamento("101") == [
        {"nome": "Joana Ribeiro", "data": "2030-04-21"}
    ]


async def test_confirmacao_so_uma_resposta_vence(repo: RepositorioCondominio):
    await repo.registrar_confirmacao("c1", "s1", "reservar", {"area": "salao-de-festas"})
    assert [c["id"] for c in await repo.confirmacoes_pendentes("s1")] == ["c1"]
    # 10 respostas simultaneas ao mesmo id: exatamente uma vence.
    r = await asyncio.gather(*(repo.responder_confirmacao("c1", "s1", True) for _ in range(10)))
    assert sum(r) == 1
    assert await repo.confirmacoes_pendentes("s1") == []
    # Reenvio (ja respondida), id inexistente e id de outra sessao: todos recusados.
    assert not await repo.responder_confirmacao("c1", "s1", True)
    assert not await repo.responder_confirmacao("id-inexistente", "s1", True)
    await repo.registrar_confirmacao("c2", "s2", "reservar", {})
    assert not await repo.responder_confirmacao("c2", "s1", True)
    assert await repo.responder_confirmacao("c2", "s2", False)
