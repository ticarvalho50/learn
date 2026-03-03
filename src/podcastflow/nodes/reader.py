"""Nó Reader — lê e normaliza o arquivo local de notícias (JSON, CSV ou TXT)."""

import csv
import json
import logging
from pathlib import Path

from podcastflow.state import PodcastState

logger = logging.getLogger(__name__)


def reader_load(state: PodcastState) -> dict:
    """Lê o arquivo de notícias e normaliza para lista de dicts.

    Suporta três formatos:
    - JSON: lista de objetos com qualquer estrutura
    - CSV: cada linha vira um dict com as colunas como chaves
    - TXT: cada bloco separado por linha em branco vira um artigo {\"text\": ...}

    Args:
        state: Estado atual do grafo.

    Returns:
        Dicionário com os campos atualizados: raw_articles, topic, metadata.
    """
    input_file = state["input_file"]
    logger.info("reader_load | lendo arquivo: %s", input_file)

    path = Path(input_file)
    if not path.exists():
        logger.error("reader_load | arquivo não encontrado: %s", input_file)
        raise FileNotFoundError(f"Arquivo de notícias não encontrado: {input_file}")

    suffix = path.suffix.lower()

    try:
        if suffix == ".json":
            articles = _load_json(path)
        elif suffix == ".csv":
            articles = _load_csv(path)
        elif suffix in (".txt", ".md"):
            articles = _load_txt(path)
        else:
            raise ValueError(f"Formato não suportado: {suffix}. Use .json, .csv ou .txt")
    except Exception as exc:
        logger.error("reader_load | erro ao ler arquivo: %s", exc)
        raise

    if not articles:
        raise ValueError(f"Arquivo '{input_file}' não contém artigos válidos.")

    # Deriva um tema do arquivo se não estiver no state
    topic = state.get("topic") or path.stem.replace("_", " ").replace("-", " ").title()

    logger.info("reader_load | %d artigos carregados | tema: %s", len(articles), topic)

    metadata = state.get("metadata", {})
    metadata.update(
        {
            "input_file": str(path.resolve()),
            "article_count": len(articles),
            "file_format": suffix,
        }
    )

    return {
        "raw_articles": articles,
        "topic": topic,
        "metadata": metadata,
    }


# ---------------------------------------------------------------------------
# Helpers de leitura por formato
# ---------------------------------------------------------------------------


def _load_json(path: Path) -> list[dict]:
    """Carrega notícias de um arquivo JSON.

    Aceita:
    - Lista direta: [{...}, {...}]
    - Objeto com chave "articles", "news", "items" ou "data": {"articles": [...]}
    """
    with path.open(encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, list):
        return data

    # Tenta encontrar uma chave de lista dentro do objeto
    for key in ("articles", "news", "items", "data", "results"):
        if key in data and isinstance(data[key], list):
            return data[key]

    raise ValueError(
        "JSON deve ser uma lista de artigos ou um objeto com chave "
        "'articles', 'news', 'items', 'data' ou 'results'."
    )


def _load_csv(path: Path) -> list[dict]:
    """Carrega notícias de um arquivo CSV (com cabeçalho)."""
    articles = []
    with path.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            articles.append(dict(row))
    return articles


def _load_txt(path: Path) -> list[dict]:
    """Carrega notícias de um arquivo TXT.

    Cada bloco separado por linha em branco é tratado como um artigo.
    A primeira linha do bloco é considerada o título.
    """
    content = path.read_text(encoding="utf-8").strip()
    blocks = [b.strip() for b in content.split("\n\n") if b.strip()]

    articles = []
    for block in blocks:
        lines = block.splitlines()
        title = lines[0] if lines else "Sem título"
        body = "\n".join(lines[1:]).strip() if len(lines) > 1 else title
        articles.append({"title": title, "text": body})

    return articles
