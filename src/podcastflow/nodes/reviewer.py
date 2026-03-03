"""Nó Reviewer — revisa e aprova/reprova o roteiro gerado."""

import json
import logging
import re

from langchain_google_genai import ChatGoogleGenerativeAI

from podcastflow.configuration import config
from podcastflow.prompts import reviewer_prompt
from podcastflow.state import PodcastState

logger = logging.getLogger(__name__)


def reviewer_check(state: PodcastState) -> dict:
    """Revisa o roteiro e decide se está aprovado para produção.

    Args:
        state: Estado atual com 'script' e 'analysis' preenchidos.

    Returns:
        Dicionário com 'review_approved', 'review_feedback' e 'review_iterations'.
    """
    cfg = state.get("config", {})
    tone = cfg.get("tone", config.tone)
    audience = cfg.get("audience", config.audience)
    language = cfg.get("language", config.language)
    max_iterations = cfg.get("max_review_iterations", config.max_review_iterations)

    iteration = state.get("review_iterations", 0) + 1
    logger.info("reviewer_check | revisão #%d", iteration)

    # Força aprovação se atingiu o limite de iterações
    if iteration > max_iterations:
        logger.warning(
            "reviewer_check | limite de %d iterações atingido — forçando aprovação",
            max_iterations,
        )
        return {
            "review_approved": True,
            "review_feedback": "",
            "review_iterations": iteration,
        }

    llm = ChatGoogleGenerativeAI(
        model=config.llm_model,
        temperature=config.llm_temperature_analytic,
        google_api_key=config.google_api_key,
    )

    chain = reviewer_prompt | llm

    result = chain.invoke(
        {
            "tone": tone,
            "audience": audience,
            "language": language,
            "analysis": state["analysis"],
            "script": state["script"],
        }
    )

    raw = result.content.strip()
    review = _parse_review_json(raw)

    approved: bool = review.get("approved", False)
    feedback: str = review.get("feedback", "")
    score: int = review.get("score", 0)
    issues: list = review.get("issues", [])

    if approved:
        logger.info("reviewer_check | APROVADO | score=%d", score)
    else:
        logger.warning(
            "reviewer_check | REPROVADO | score=%d | issues=%s", score, issues
        )

    return {
        "review_approved": approved,
        "review_feedback": feedback if not approved else "",
        "review_iterations": iteration,
    }


def _parse_review_json(raw: str) -> dict:
    """Extrai o JSON da resposta do LLM, tolerando texto ao redor.

    Args:
        raw: Resposta bruta do LLM.

    Returns:
        Dicionário com os campos do review.
    """
    # Tenta direto
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    # Tenta extrair bloco JSON com regex
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    logger.error("reviewer_check | não foi possível parsear JSON: %s", raw[:200])
    # Fallback seguro: reprova para forçar nova tentativa
    return {"approved": False, "feedback": "Erro ao parsear resposta do revisor.", "issues": []}
