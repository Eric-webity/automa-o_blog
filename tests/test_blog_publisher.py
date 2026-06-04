"""Testes do publicador de blog local."""

import asyncio

from db.database import init_db
from db.repository import ArticleRepository, UserRepository
from services.blog_publisher import save_post_to_blog


def test_save_post_to_blog_creates_record(tmp_path, monkeypatch) -> None:
    """Salva matéria no SQLite local."""
    db_file = tmp_path / "test.db"
    monkeypatch.setattr("config.paths.DATA_DIR", tmp_path)
    monkeypatch.setattr("config.paths.DB_PATH", db_file)
    monkeypatch.setattr("db.database.DATA_DIR", tmp_path)
    monkeypatch.setattr("db.database.DB_PATH", db_file)
    monkeypatch.setattr("db.database._engine", None)
    monkeypatch.setattr("db.database._SessionLocal", None)

    init_db()
    user = UserRepository().create(
        name="Publisher Test",
        email="pub@test.local",
        password="secret123",
    )
    result = asyncio.run(
        save_post_to_blog(
            title="Teste GEO",
            markdown_content="# Artigo de teste",
            user_id=user.id,
        )
    )
    assert result.article_id > 0
    record = ArticleRepository(user_id=user.id).get_by_id(result.article_id)
    assert record is not None
    assert record.title == "Teste GEO"
