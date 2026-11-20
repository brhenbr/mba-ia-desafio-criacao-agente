"""Infraestrutura dos testes de ponta a ponta (e2e).

Estes testes usam o Gemini REAL, o PostgreSQL real e a API real (um processo uvicorn
iniciado aqui). Gastam creditos do Google AI Studio. Rodam num banco proprio
(`aurora_e2e`), sem tocar nos dados de desenvolvimento.

Como rodar: veja docs/testes.md.
"""

import importlib.metadata
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

import asyncpg
import httpx
import pytest

from app.config import get_settings
from scripts.restaurar import restaurar

RAIZ = Path(__file__).resolve().parents[2]
BANCO_E2E = "aurora_e2e"
PORTA = int(os.environ.get("E2E_PORTA", "8001"))
BASE = f"http://localhost:{PORTA}"
RELATORIO = Path(
    os.environ.get("E2E_RELATORIO", RAIZ / "docs" / "evidencias" / "e2e-ultima-execucao.md")
)


class Registro:
    """Acumula tudo o que acontece no fluxo para gerar o relatorio de evidencias."""

    def __init__(self) -> None:
        self.linhas: list[str] = []
        self.verificacoes = 0

    def passo(self, titulo: str) -> None:
        self.linhas += ["", f"### {titulo}", ""]

    def texto(self, t: str) -> None:
        self.linhas.append(t)

    def verificar(self, descricao: str, condicao: bool) -> None:
        self.verificacoes += 1
        self.linhas.append(f"- {'✅' if condicao else '❌'} {descricao}")
        assert condicao, descricao


class Servidor:
    """Processo uvicorn da API, que pode ser reiniciado (passo 13)."""

    def __init__(self) -> None:
        self.proc: subprocess.Popen | None = None

    def iniciar(self) -> None:
        env = {**os.environ, "POSTGRES_DB": BANCO_E2E, "PYTHONIOENCODING": "utf-8"}
        self.proc = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "app.main:app", "--port", str(PORTA)],
            cwd=RAIZ,
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        limite = time.time() + 90
        while time.time() < limite:
            try:
                if httpx.get(f"{BASE}/apartamentos/101/reservas", timeout=2).status_code == 200:
                    return
            except httpx.HTTPError:
                pass
            if self.proc.poll() is not None:
                break
            time.sleep(1)
        self.parar()
        raise RuntimeError("A API nao subiu a tempo.")

    def parar(self) -> None:
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=15)
            except subprocess.TimeoutExpired:
                self.proc.kill()
        self.proc = None

    def reiniciar(self) -> None:
        self.parar()
        self.iniciar()


async def _criar_banco() -> str:
    s = get_settings()
    conn = await asyncpg.connect(
        user=s.postgres_user,
        password=s.postgres_password,
        host=s.postgres_host,
        port=s.postgres_port,
        database=s.postgres_db,
    )
    if not await conn.fetchval("SELECT 1 FROM pg_database WHERE datname = $1", BANCO_E2E):
        await conn.execute(f"CREATE DATABASE {BANCO_E2E}")
    await conn.close()
    return (
        f"postgresql+asyncpg://{s.postgres_user}:{s.postgres_password}"
        f"@{s.postgres_host}:{s.postgres_port}/{BANCO_E2E}"
    )


@pytest.fixture(scope="module")
def registro():
    r = Registro()
    yield r
    s = get_settings()
    cabecalho = [
        "# Evidência: fluxo do avaliador (e2e)",
        "",
        "Relatório gerado automaticamente por `tests/e2e/test_fluxo_avaliador.py`.",
        "Execução **real**: API (uvicorn), PostgreSQL e Gemini de verdade, sem simulações.",
        "",
        f"- Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"- Modelo do agente principal: `{s.modelo_principal}`",
        f"- Modelo dos especialistas: `{s.modelo_especialistas}`",
        f"- google-adk: `{importlib.metadata.version('google-adk')}`",
        f"- Verificações executadas: {r.verificacoes}",
        "",
        (
            "Legenda: `>` mensagem do morador, `<` resposta do assistente, "
            "✅ verificação que passou, ❌ verificação que falhou."
        ),
    ]
    RELATORIO.parent.mkdir(parents=True, exist_ok=True)
    RELATORIO.write_text("\n".join(cabecalho + r.linhas) + "\n", encoding="utf-8")


@pytest.fixture(scope="module")
def servidor():
    if not os.environ.get("GOOGLE_API_KEY") and not get_settings().modelo_principal:
        pytest.skip("Configure o .env (GOOGLE_API_KEY e modelos) para rodar os testes e2e.")
    import asyncio

    url = asyncio.run(_criar_banco())
    restaurar(url)  # estado inicial limpo no banco e2e
    srv = Servidor()
    srv.iniciar()
    yield srv
    srv.parar()


@pytest.fixture(scope="module")
def api(servidor):
    with httpx.Client(base_url=BASE, timeout=180) as c:
        yield c
