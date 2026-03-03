"""Definição principal do grafo LangGraph do PodcastFlow.

Fluxo:
    reader → analyst → scriptwriter → reviewer → (loop se reprovado)
                                                ↓ (aprovado)
                                          social_media → tts → END
"""

import logging

from langgraph.graph import END, START, StateGraph

from podcastflow.nodes import (
    analyst_synthesize,
    reader_load,
    reviewer_check,
    scriptwriter_generate,
    social_media_generate,
    tts_narrate,
)
from podcastflow.state import PodcastState

logger = logging.getLogger(__name__)


def _route_after_review(state: PodcastState) -> str:
    """Decide o próximo nó após a revisão.

    Args:
        state: Estado atual com 'review_approved' preenchido.

    Returns:
        Nome do próximo nó: 'scriptwriter' (reescrita) ou 'social_media' (aprovado).
    """
    if state.get("review_approved", False):
        logger.info("graph | roteiro APROVADO — seguindo para social_media e TTS")
        return "social_media"
    logger.info(
        "graph | roteiro REPROVADO (iteração %d) — voltando para scriptwriter",
        state.get("review_iterations", 1),
    )
    return "scriptwriter"


def build_graph() -> StateGraph:
    """Constrói e compila o grafo LangGraph do PodcastFlow.

    Returns:
        Grafo compilado pronto para execução.
    """
    builder = StateGraph(PodcastState)

    # Registra os nós
    builder.add_node("reader", reader_load)
    builder.add_node("analyst", analyst_synthesize)
    builder.add_node("scriptwriter", scriptwriter_generate)
    builder.add_node("reviewer", reviewer_check)
    builder.add_node("social_media", social_media_generate)
    builder.add_node("tts", tts_narrate)

    # Define as arestas (edges)
    builder.add_edge(START, "reader")
    builder.add_edge("reader", "analyst")
    builder.add_edge("analyst", "scriptwriter")
    builder.add_edge("scriptwriter", "reviewer")

    # Aresta condicional: aprovado → social_media | reprovado → scriptwriter
    builder.add_conditional_edges(
        "reviewer",
        _route_after_review,
        {"social_media": "social_media", "scriptwriter": "scriptwriter"},
    )

    builder.add_edge("social_media", "tts")
    builder.add_edge("tts", END)

    return builder.compile()


# Instância compilada exportada para uso direto e para visualização
graph = build_graph()
