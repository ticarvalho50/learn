"""Nó ScriptWriter — gera o roteiro do podcast."""

import logging

from langchain_google_genai import ChatGoogleGenerativeAI

from podcastflow.configuration import config
from podcastflow.prompts import (
    DURATION_MINUTES,
    HOSTS_LABEL,
    SCRIPTWRITER_FEEDBACK_SECTION,
    scriptwriter_prompt,
)
from podcastflow.state import PodcastState

logger = logging.getLogger(__name__)


def scriptwriter_generate(state: PodcastState) -> dict:
    """Gera o roteiro do podcast a partir da análise.

    Se houver feedback de revisão anterior, inclui no prompt para correção.

    Args:
        state: Estado atual com 'analysis' preenchido.

    Returns:
        Dicionário com o campo 'script' atualizado.
    """
    cfg = state.get("config", {})

    tone = cfg.get("tone", config.tone)
    duration = cfg.get("duration", config.duration)
    audience = cfg.get("audience", config.audience)
    hosts = cfg.get("hosts", config.hosts)
    language = cfg.get("language", config.language)

    review_feedback = state.get("review_feedback", "")
    iteration = state.get("review_iterations", 0)

    logger.info(
        "scriptwriter_generate | gerando roteiro | tom=%s | duração=%s | iteração=%d",
        tone,
        duration,
        iteration,
    )

    llm = ChatGoogleGenerativeAI(
        model=config.llm_model,
        temperature=config.llm_temperature_creative,
        google_api_key=config.google_api_key,
    )

    chain = scriptwriter_prompt | llm

    feedback_section = ""
    if review_feedback:
        feedback_section = SCRIPTWRITER_FEEDBACK_SECTION.format(
            review_feedback=review_feedback
        )

    result = chain.invoke(
        {
            "language": language,
            "tone": tone,
            "duration": duration,
            "duration_minutes": DURATION_MINUTES.get(duration, 15),
            "hosts": hosts,
            "hosts_label": HOSTS_LABEL.get(hosts, "dois apresentadores"),
            "audience": audience,
            "analysis": state["analysis"],
            "feedback_section": feedback_section,
        }
    )

    script = result.content
    logger.info("scriptwriter_generate | roteiro gerado (%d chars)", len(script))

    return {
        "script": script,
        "review_feedback": "",  # limpa feedback anterior após reescrita
    }
