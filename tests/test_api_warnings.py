"""Testes de campos de aviso na API de geração."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from starlette.testclient import TestClient

from api.routes import create_api_app
from db.database import init_db
from services.blog.generator import BlogPostPackage
from services.blog_pipeline import BlogResult


@pytest.fixture
def api_client(tmp_path, monkeypatch):
    db_file = tmp_path / "api_warn.db"
    monkeypatch.setattr("config.paths.DATA_DIR", tmp_path)
    monkeypatch.setattr("config.paths.DB_PATH", db_file)
    monkeypatch.setattr("db.database.DATA_DIR", tmp_path)
    monkeypatch.setattr("db.database.DB_PATH", db_file)
    monkeypatch.setattr("db.database._engine", None)
    monkeypatch.setattr("db.database._SessionLocal", None)
    monkeypatch.setenv("GEO_ENV", "development")
    monkeypatch.delenv("GEO_API_KEY", raising=False)

    init_db()
    with TestClient(create_api_app()) as client:
        yield client


def _mock_result() -> BlogResult:
    pkg = BlogPostPackage(
        markdown="# Artigo\n\nCorpo.",
        meta_title="Título API",
        meta_description="Descrição com comprimento adequado para meta description de testes.",
        slug="artigo-api",
        keywords_used=["geo"],
        skeleton=object(),
        word_count_target=2000,
        word_count_actual=1200,
        used_llm=True,
        provider_used="openai",
        generation_mode="standard",
    )
    return BlogResult(
        package=pkg,
        meta_payload={"meta_title": pkg.meta_title},
        md_path="/tmp/a.md",
        meta_path="/tmp/b.json",
        index_path=None,
        article_id=42,
        fallback_reason=None,
        warning=(
            "Revisão recomendada: o texto tem 1,200 de 2,000 palavras pedidas "
            "(60% da meta, faltam cerca de 800)."
        ),
        similarity_warning=(
            "Texto muito parecido com uma fonte de referência (~90% de similaridade). "
            "Reescreva com palavras próprias, cite a fonte ou use aspas antes de publicar."
        ),
    )


def test_generate_response_includes_warnings(api_client: TestClient) -> None:
    with patch("api.routes.run_blog_pipeline", return_value=_mock_result()):
        with patch("api.routes.notify_article_generated", return_value=None):
            response = api_client.post(
                "/api/v1/articles/generate",
                json={
                    "topic": "Tema de teste API",
                    "reference_urls": [],
                    "word_count": 2000,
                    "use_llm": False,
                    "save_to_db": False,
                    "notify_webhook": False,
                },
            )
    assert response.status_code == 200
    body = response.json()
    assert body["warning"]
    assert body["similarity_warning"]
    assert len(body["warnings"]) == 2
    assert body["warning"] in body["warnings"]
