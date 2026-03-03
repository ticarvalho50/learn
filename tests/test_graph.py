"""Testes do grafo LangGraph (estrutura, não execução completa)."""

from podcastflow.graph import build_graph


def test_graph_builds_without_error() -> None:
    """Verifica que o grafo é compilado sem exceções."""
    g = build_graph()
    assert g is not None


def test_graph_has_expected_nodes() -> None:
    """Verifica que todos os nós esperados estão registrados."""
    g = build_graph()
    node_names = set(g.nodes.keys())
    expected = {"reader", "analyst", "scriptwriter", "reviewer", "social_media", "tts"}
    assert expected.issubset(node_names), f"Nós faltando: {expected - node_names}"
