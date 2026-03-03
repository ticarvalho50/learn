"""Nó SocialMedia — gera posts para redes sociais a partir do roteiro."""

import json
import logging
import re

from langchain_google_genai import ChatGoogleGenerativeAI

from podcastflow.configuration import config
from podcastflow.prompts import social_media_prompt
from podcastflow.state import PodcastState

logger = logging.getLogger(__name__)


def social_media_generate(state: PodcastState) -> dict:
    """Gera posts adaptados para Twitter, Instagram e LinkedIn.

    Args:
        state: Estado atual com 'script' aprovado.

    Returns:
        Dicionário com o campo 'social_posts' atualizado.
    """
    cfg = state.get("config", {})
    tone = cfg.get("tone", config.tone)
    language = cfg.get("language", config.language)

    logger.info("social_media_generate | gerando posts para 3 plataformas")

    llm = ChatGoogleGenerativeAI(
        model=config.llm_model,
        temperature=config.llm_temperature_creative,
        google_api_key=config.google_api_key,
    )

    chain = social_media_prompt | llm

    result = chain.invoke(
        {
            "language": language,
            "tone": tone,
            "script": state["script"],
        }
    )

    raw = result.content.strip()
    posts = _parse_posts_json(raw)

    logger.info(
        "social_media_generate | posts gerados | twitter=%d chars | instagram=%d chars | linkedin=%d chars",
        len(posts.get("twitter", "")),
        len(posts.get("instagram", "")),
        len(posts.get("linkedin", "")),
    )

    return {"social_posts": posts}


def _parse_posts_json(raw: str) -> dict[str, str]:
    """Extrai o JSON de posts da resposta do LLM.

    Args:
        raw: Resposta bruta do LLM.

    Returns:
        Dicionário com chaves twitter, instagram, linkedin.
    """
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    logger.error("social_media_generate | falha ao parsear JSON, retornando texto bruto")
    return {"twitter": raw[:280], "instagram": raw[:300], "linkedin": raw[:800]}
