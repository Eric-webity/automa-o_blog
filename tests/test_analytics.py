"""Testes de métricas do dashboard."""

from __future__ import annotations

from db.database import init_db
from db.repository import ArticleRepository


def test_count_llm_articles(tmp_path, monkeypatch) -> None:
    """Conta matérias com metadados de IA no json_index."""
    db_file = tmp_path / "analytics.db"
    monkeypatch.setattr("config.paths.DATA_DIR", tmp_path)
    monkeypatch.setattr("config.paths.DB_PATH", db_file)
    monkeypatch.setattr("db.database.DATA_DIR", tmp_path)
    monkeypatch.setattr("db.database.DB_PATH", db_file)
    monkeypatch.setattr("db.database._engine", None)
    monkeypatch.setattr("db.database._SessionLocal", None)

    init_db()
    repo = ArticleRepository()
    repo.create(
        title="Com IA",
        markdown_content="# teste",
        json_index={"used_llm": True, "generation_mode": "openai"},
    )
    repo.create(
        title="Local",
        markdown_content="# local",
        json_index={"used_llm": False, "generation_mode": "local"},
    )
    assert repo.count_llm_articles() == 1
