"""Testes dos nós do PodcastFlow."""

import json
import tempfile
from pathlib import Path

import pytest

from podcastflow.nodes.reader import reader_load
from podcastflow.utils.helpers import articles_to_text


# ---------------------------------------------------------------------------
# reader_load
# ---------------------------------------------------------------------------


def _base_state(input_file: str) -> dict:
    return {
        "input_file": input_file,
        "topic": "",
        "raw_articles": [],
        "analysis": "",
        "script": "",
        "review_feedback": "",
        "review_approved": False,
        "review_iterations": 0,
        "audio_path": "",
        "social_posts": {},
        "metadata": {},
        "config": {},
    }


def test_reader_load_json(tmp_path: Path) -> None:
    articles = [
        {"title": "Notícia 1", "text": "Conteúdo da notícia 1."},
        {"title": "Notícia 2", "text": "Conteúdo da notícia 2."},
    ]
    f = tmp_path / "noticias.json"
    f.write_text(json.dumps(articles), encoding="utf-8")

    result = reader_load(_base_state(str(f)))

    assert len(result["raw_articles"]) == 2
    assert result["raw_articles"][0]["title"] == "Notícia 1"
    assert result["topic"] == "Noticias"


def test_reader_load_json_with_key(tmp_path: Path) -> None:
    data = {"articles": [{"title": "A", "text": "B"}]}
    f = tmp_path / "feed.json"
    f.write_text(json.dumps(data), encoding="utf-8")

    result = reader_load(_base_state(str(f)))
    assert len(result["raw_articles"]) == 1


def test_reader_load_csv(tmp_path: Path) -> None:
    f = tmp_path / "noticias.csv"
    f.write_text("title,text\nNotícia CSV,Corpo da notícia\n", encoding="utf-8")

    result = reader_load(_base_state(str(f)))
    assert len(result["raw_articles"]) == 1
    assert result["raw_articles"][0]["title"] == "Notícia CSV"


def test_reader_load_txt(tmp_path: Path) -> None:
    content = "Título da Notícia 1\nCorpo da primeira notícia aqui.\n\nTítulo 2\nCorpo dois."
    f = tmp_path / "noticias.txt"
    f.write_text(content, encoding="utf-8")

    result = reader_load(_base_state(str(f)))
    assert len(result["raw_articles"]) == 2
    assert result["raw_articles"][0]["title"] == "Título da Notícia 1"


def test_reader_load_file_not_found() -> None:
    with pytest.raises(FileNotFoundError):
        reader_load(_base_state("/nao/existe.json"))


def test_reader_load_unsupported_format(tmp_path: Path) -> None:
    f = tmp_path / "data.xml"
    f.write_text("<root/>", encoding="utf-8")
    with pytest.raises(ValueError, match="Formato não suportado"):
        reader_load(_base_state(str(f)))


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def test_articles_to_text_basic() -> None:
    articles = [
        {"title": "Título", "text": "Corpo.", "source": "G1"},
        {"headline": "Outro", "content": "Texto.", "url": "http://x.com"},
    ]
    text = articles_to_text(articles)
    assert "Título" in text
    assert "Corpo." in text
    assert "G1" in text
    assert "Outro" in text


def test_articles_to_text_unknown_fields() -> None:
    # Sem campos conhecidos — usa str(article)
    articles = [{"campo_custom": "valor"}]
    text = articles_to_text(articles)
    assert "Artigo 1" in text
