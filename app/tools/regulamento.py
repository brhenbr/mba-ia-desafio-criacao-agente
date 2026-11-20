from google.adk.tools import FunctionTool

from app.regulamento.busca import buscar


async def consultar_regulamento(pergunta: str) -> dict:
    """Busca no regulamento interno os artigos relevantes para a pergunta do morador.

    Args:
        pergunta: a duvida do morador, com as palavras-chave do assunto.
    """
    artigos = buscar(pergunta)
    if not artigos:
        return {"status": "sem_resultado", "mensagem": "Nada encontrado no regulamento."}
    return {
        "status": "ok",
        "trechos": [{"capitulo": a.capitulo, "texto": a.texto} for a in artigos],
    }


tool_regulamento = FunctionTool(consultar_regulamento)
