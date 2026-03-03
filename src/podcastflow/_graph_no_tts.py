"""Variante do grafo sem o nó TTS — usada com a flag --no-tts."""

from langgraph.graph import END, START, StateGraph

from podcastflow.nodes import (
    analyst_synthesize,
    reader_load,
    reviewer_check,
    scriptwriter_generate,
    social_media_generate,
)
from podcastflow.state import PodcastState


def _route_after_review(state: PodcastState) -> str:
    return "social_media" if state.get("review_approved", False) else "scriptwriter"


def _build() -> StateGraph:
    builder = StateGraph(PodcastState)
    builder.add_node("reader", reader_load)
    builder.add_node("analyst", analyst_synthesize)
    builder.add_node("scriptwriter", scriptwriter_generate)
    builder.add_node("reviewer", reviewer_check)
    builder.add_node("social_media", social_media_generate)

    builder.add_edge(START, "reader")
    builder.add_edge("reader", "analyst")
    builder.add_edge("analyst", "scriptwriter")
    builder.add_edge("scriptwriter", "reviewer")
    builder.add_conditional_edges(
        "reviewer",
        _route_after_review,
        {"social_media": "social_media", "scriptwriter": "scriptwriter"},
    )
    builder.add_edge("social_media", END)
    return builder.compile()


graph = _build()
