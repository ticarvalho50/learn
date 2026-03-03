"""Funções auxiliares compartilhadas entre os nós."""

import json
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

# Campos preferidos para extrair o texto principal de um artigo
_TEXT_FIELDS = ("text", "content", "body", "description", "summary", "conteudo", "texto")
_TITLE_FIELDS = ("title", "titulo", "headline", "name")
_SOURCE_FIELDS = ("source", "fonte", "url", "link", "author", "autor")


def articles_to_text(articles: list[dict]) -> str:
    """Converte lista de artigos em texto formatado para o LLM.

    Tenta extrair título, fonte e corpo de cada artigo independente
    dos nomes de campos do arquivo de entrada.

    Args:
        articles: Lista de dicionários representando artigos.

    Returns:
        Texto formatado com todos os artigos numerados.
    """
    lines: list[str] = []

    for i, article in enumerate(articles, start=1):
        title = _extract_field(article, _TITLE_FIELDS) or f"Artigo {i}"
        source = _extract_field(article, _SOURCE_FIELDS) or "fonte desconhecida"
        body = _extract_field(article, _TEXT_FIELDS) or str(article)

        lines.append(f"### Artigo {i}: {title}")
        lines.append(f"**Fonte:** {source}")
        lines.append(body.strip())
        lines.append("")

    return "\n".join(lines)


def save_output(state: dict, output_dir: str = "outputs") -> Path:
    """Salva o resultado completo da execução em um arquivo JSON.

    Args:
        state: Estado final do grafo.
        output_dir: Diretório de saída.

    Returns:
        Caminho do arquivo salvo.
    """
    path = Path(output_dir)
    path.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    topic_slug = _slugify(state.get("topic", "podcast"))[:40]
    filename = path / f"{timestamp}_{topic_slug}_output.json"

    output = {
        "topic": state.get("topic"),
        "script": state.get("script"),
        "analysis": state.get("analysis"),
        "social_posts": state.get("social_posts"),
        "audio_path": state.get("audio_path"),
        "metadata": state.get("metadata"),
    }

    with filename.open("w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    logger.info("helpers | output salvo: %s", filename)
    return filename


def _extract_field(article: dict, candidates: tuple[str, ...]) -> str | None:
    """Busca o primeiro campo disponível no dicionário.

    Args:
        article: Dicionário do artigo.
        candidates: Nomes de campo a tentar em ordem.

    Returns:
        Valor do campo encontrado ou None.
    """
    for field in candidates:
        if field in article and article[field]:
            return str(article[field])
    return None


def _slugify(text: str) -> str:
    """Converte texto para formato de slug (snake_case sem acentos).

    Args:
        text: Texto a converter.

    Returns:
        Slug gerado.
    """
    import re
    import unicodedata

    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^\w\s-]", "", text).strip().lower()
    return re.sub(r"[\s-]+", "_", text)
