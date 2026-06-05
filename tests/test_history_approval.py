"""Aprovação de rascunhos e permissões no histórico."""

from __future__ import annotations

import asyncio

from db.database import init_db
from db.models import ArticleStatus, UserRole
from db.repository import ArticleRepository, UserRepository
from services.blog_publisher import save_post_to_blog
from ui.history_scope import history_mutate_owner_id, record_accessible


def _setup_db(tmp_path, monkeypatch) -> None:
    db_file = tmp_path / "approval.db"
    monkeypatch.setattr("config.paths.DATA_DIR", tmp_path)
    monkeypatch.setattr("config.paths.DB_PATH", db_file)
    monkeypatch.setattr("db.database.DATA_DIR", tmp_path)
    monkeypatch.setattr("db.database.DB_PATH", db_file)
    monkeypatch.setattr("db.database._engine", None)
    monkeypatch.setattr("db.database._SessionLocal", None)
    init_db()


def test_approve_draft_sets_completed(tmp_path, monkeypatch) -> None:
    _setup_db(tmp_path, monkeypatch)
    user = UserRepository().create(
        name="Autor",
        email="autor@test.local",
        password="secret12345",
    )
    article = ArticleRepository(user_id=user.id).create(
        title="Rascunho",
        markdown_content="# Olá",
        status=ArticleStatus.DRAFT.value,
        user_id=user.id,
    )

    async def _run():
        owner_id, err = history_mutate_owner_id(
            article,
            session_user_id=user.id,
            is_admin=False,
            scope_user_id=None,
        )
        assert err is None
        return await save_post_to_blog(
            title=article.title,
            markdown_content="# Olá mundo",
            article_id=article.id,
            status=ArticleStatus.COMPLETED.value,
            user_id=owner_id,
        )

    result = asyncio.run(_run())
    updated = ArticleRepository(user_id=user.id).get_by_id(result.article_id)
    assert updated is not None
    assert updated.status == ArticleStatus.COMPLETED.value


def test_user_cannot_mutate_admin_draft(tmp_path, monkeypatch) -> None:
    _setup_db(tmp_path, monkeypatch)
    admin = UserRepository().create(
        name="Admin",
        email="admin@test.local",
        password="secret12345",
    )
    assert admin.role == UserRole.ADMIN.value
    user = UserRepository().create(
        name="Maria",
        email="maria@test.local",
        password="secret12345",
    )
    article = ArticleRepository(user_id=admin.id).create(
        title="Admin draft",
        markdown_content="# x",
        status=ArticleStatus.DRAFT.value,
        user_id=admin.id,
    )

    assert not record_accessible(
        article,
        session_user_id=user.id,
        is_admin=False,
    )
    owner_id, err = history_mutate_owner_id(
        article,
        session_user_id=user.id,
        is_admin=False,
        scope_user_id=None,
    )
    assert owner_id is None
    assert err
