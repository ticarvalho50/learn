"""Definição do estado compartilhado do grafo LangGraph."""

from typing import TypedDict


class PodcastState(TypedDict):
    """Estado compartilhado entre todos os nós do grafo PodcastFlow.

    Attributes:
        input_file: Caminho para o arquivo de notícias (JSON/CSV/TXT).
        topic: Tema/título do episódio (derivado das notícias ou fornecido pelo usuário).
        raw_articles: Lista de artigos brutos lidos do arquivo de entrada.
        analysis: Síntese e análise das matérias produzida pelo Analyst.
        script: Roteiro completo do podcast gerado pelo ScriptWriter.
        review_feedback: Feedback textual do Reviewer (preenchido quando reprovado).
        review_approved: True se o roteiro foi aprovado pelo Reviewer.
        review_iterations: Contador de iterações de revisão (evita loop infinito).
        audio_path: Caminho para o arquivo de áudio gerado pelo TTS.
        social_posts: Posts gerados por plataforma (twitter, instagram, linkedin).
        metadata: Metadados da execução (timestamp, fontes, parâmetros, duração estimada).
        config: Parâmetros de configuração passados pelo usuário (tone, duration, etc.).
    """

    input_file: str
    topic: str
    raw_articles: list[dict]
    analysis: str
    script: str
    review_feedback: str
    review_approved: bool
    review_iterations: int
    audio_path: str
    social_posts: dict[str, str]
    metadata: dict
    config: dict
