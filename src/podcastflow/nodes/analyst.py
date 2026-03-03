"""Nó Analyst — analisa e sintetiza os artigos coletados."""

import logging

from langchain_google_genai import ChatGoogleGenerativeAI

from podcastflow.configuration import config
from podcastflow.prompts import analyst_prompt
from podcastflow.state import PodcastState
from podcastflow.utils.helpers import articles_to_text

logger = logging.getLogger(__name__)


def analyst_synthesize(state: PodcastState) -> dict:
    """Analisa os artigos brutos e produz uma síntese estruturada.

    Args:
        state: Estado atual do grafo com raw_articles preenchido.

    Returns:
        Dicionário com o campo 'analysis' atualizado.
    """
    articles = state["raw_articles"]
    cfg = state.get("config", {})

    language = cfg.get("language", config.language)
    audience = cfg.get("audience", config.audience)

    logger.info("analyst_synthesize | analisando %d artigos", len(articles))

    llm = ChatGoogleGenerativeAI(
        model=config.llm_model,
        temperature=config.llm_temperature_analytic,
        google_api_key=config.google_api_key,
    )

    chain = analyst_prompt | llm

    articles_text = articles_to_text(articles)

    result = chain.invoke(
        {
            "language": language,
            "audience": audience,
            "articles": articles_text,
        }
    )

    analysis = result.content
    logger.info("analyst_synthesize | análise concluída (%d chars)", len(analysis))

    return {"analysis": analysis}
