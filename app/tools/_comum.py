"""Utilitarios compartilhados pelas tools.

GARANTIA 2: o apartamento usado pelas tools vem SEMPRE do state da sessao, gravado
uma unica vez na criacao da sessao. Nenhuma tool tem parametro `apartamento`, entao
nada que o modelo (ou o morador) escreva pode apontar para outro apartamento.
"""

from datetime import date

from google.adk.tools import ToolContext

CHAVE_APARTAMENTO = "apartamento"


def apartamento_da_sessao(tool_context: ToolContext) -> str | None:
    valor = tool_context.state.get(CHAVE_APARTAMENTO)
    return str(valor) if valor else None


def interpretar_data(texto: str) -> date | None:
    try:
        return date.fromisoformat(texto.strip())
    except (ValueError, AttributeError):
        return None


SEM_SESSAO = {"status": "erro", "mensagem": "Sessao sem apartamento definido."}
DATA_INVALIDA = {"status": "erro", "mensagem": "Data invalida. Use o formato AAAA-MM-DD."}
