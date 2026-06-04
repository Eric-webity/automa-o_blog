"""Isolamento de matérias por user_id."""

from __future__ import annotations

from db.database import init_db
from db.repository import ArticleRepository, UserRepository


def _setup_db(tmp_path, monkeypatch) -> None:
    db_file = tmp_path / "scope.db"
    monkeypatch.setattr("config.paths.DATA_DIR", tmp_path)
    monkeypatch.setattr("config.paths.DB_PATH", db_file)
    monkeypatch.setattr("db.database.DATA_DIR", tmp_path)
    monkeypatch.setattr("db.database.DB_PATH", db_file)
    monkeypatch.setattr("db.database._engine", None)
    monkeypatch.setattr("db.database._SessionLocal", None)
    init_db()


def test_articles_isolated_between_users(tmp_path, monkeypatch) -> None:
    _setup_db(tmp_path, monkeypatch)
    user_a = UserRepository().create(
        name="Alice",
        email="alice@test.local",
        password="secret123",
    )
    user_b = UserRepository().create(
        name="Bob",
        email="bob@test.local",
        password="secret456",
    )

    repo_a = ArticleRepository(user_id=user_a.id)
    repo_b = ArticleRepository(user_id=user_b.id)

    article_a = repo_a.create(
        title="Matéria A",
        markdown_content="# A",
        user_id=user_a.id,
    )
    repo_b.create(title="Matéria B", markdown_content="# B", user_id=user_b.id)

    assert repo_a.list_all() == [article_a]
    assert repo_b.get_by_id(article_a.id) is None
    assert repo_a.delete(article_a.id) is True
    assert repo_b.get_by_id(article_a.id) is None


def test_user_cannot_update_other_users_article(tmp_path, monkeypatch) -> None:
    _setup_db(tmp_path, monkeypatch)
    user_a = UserRepository().create(
        name="Alice",
        email="alice2@test.local",
        password="secret123",
    )
    user_b = UserRepository().create(
        name="Bob",
        email="bob2@test.local",
        password="secret456",
    )
    repo_a = ArticleRepository(user_id=user_a.id)
    article = repo_a.create(
        title="Privada",
        markdown_content="# segredo",
        user_id=user_a.id,
    )
    repo_b = ArticleRepository(user_id=user_b.id)
    assert repo_b.update(article.id, title="Hack") is None
    assert repo_b.get_by_id(article.id) is None
    still = repo_a.get_by_id(article.id)
    assert still is not None
    assert still.title == "Privada"
