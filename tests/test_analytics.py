"""Testes de métricas do dashboard."""

from __future__ import annotations

from db.database import init_db
from db.repository import ArticleRepository, UserRepository


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
    user = UserRepository().create(
        name="Analytics",
        email="analytics@test.local",
        password="secret123",
    )
    repo = ArticleRepository(user_id=user.id)
    repo.create(
        title="Com IA",
        markdown_content="# teste",
        json_index={"used_llm": True, "generation_mode": "openai"},
        user_id=user.id,
    )
    repo.create(
        title="Local",
        markdown_content="# local",
        json_index={"used_llm": False, "generation_mode": "local"},
        user_id=user.id,
    )
    assert repo.count_llm_articles() == 1
