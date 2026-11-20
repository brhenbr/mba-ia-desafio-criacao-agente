"""Busca no regulamento (GARANTIA 4: consultado, nao carregado).

O texto fica em dados/regulamento.md e e indexado por artigo na primeira consulta.
A tool devolve so os poucos artigos mais relevantes para a pergunta. Como o resultado de
uma tool vira evento da sessao, so esses trechos entram no historico, e nunca capitulos
de outros assuntos nem o texto inteiro.
"""

import re
import unicodedata
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

CAMINHO = Path(__file__).resolve().parents[2] / "dados" / "regulamento.md"
MAX_ARTIGOS = 3
STOPWORDS = {
    "qual", "quais", "como", "para", "pode", "posso", "sobre", "ate", "aos", "dos", "das",
    "que", "com", "uma", "uns", "por", "nao", "tem", "ter", "sao", "esta", "esse", "essa",
    "quando", "onde", "horas", "hora",
}  # fmt: skip


@dataclass(frozen=True)
class Artigo:
    capitulo: str
    texto: str


def _normalizar(t: str) -> str:
    return unicodedata.normalize("NFKD", t.lower()).encode("ascii", "ignore").decode()


def _radical(palavra: str) -> str:
    return palavra[:-1] if palavra.endswith("s") and len(palavra) > 4 else palavra


def _termos(texto: str) -> set[str]:
    return {_radical(w) for w in re.findall(r"[a-z]{4,}", _normalizar(texto)) if w not in STOPWORDS}


@lru_cache
def carregar_artigos() -> tuple[Artigo, ...]:
    artigos: list[list[str]] = []
    capitulo = ""
    for bloco in CAMINHO.read_text(encoding="utf-8").split("\n\n"):
        if bloco.startswith("## "):
            capitulo = bloco[3:].strip()
        elif bloco.startswith("**Art."):
            artigos.append([capitulo, bloco])
        elif artigos and not bloco.startswith("#"):
            artigos[-1][1] += "\n\n" + bloco  # incisos e paragrafos do mesmo artigo
    return tuple(Artigo(c, t) for c, t in artigos)


def buscar(pergunta: str, limite: int = MAX_ARTIGOS) -> list[Artigo]:
    termos = _termos(pergunta)
    if not termos:
        return []
    pontuados = []
    for artigo in carregar_artigos():
        pontos = len(termos & _termos(artigo.texto)) + 3 * len(termos & _termos(artigo.capitulo))
        if pontos:
            pontuados.append((pontos, artigo))
    pontuados.sort(key=lambda x: -x[0])
    return [a for _, a in pontuados[:limite]]
