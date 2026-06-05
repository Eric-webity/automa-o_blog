"""Escopo da aba Histórico (admin vs utilizador)."""

from __future__ import annotations

from db.database import init_db
from datetime import datetime, timezone

from db.models import ArticleStatus, UserRole
from db.repository import ArticleRecord, ArticleRepository, UserRepository
from ui.history_scope import (
    HISTORY_SCOPE_ALL,
    count_drafts,
    filter_drafts_only,
    filter_visible_records,
    history_import_owner_id,
    history_list_records,
    history_list_repository,
    history_stats_user_id,
    history_write_user_id,
    record_accessible,
    resolve_user_by_name,
    sort_history_records,
)


def _setup_db(tmp_path, monkeypatch) -> None:
    db_file = tmp_path / "history_scope.db"
    monkeypatch.setattr("config.paths.DATA_DIR", tmp_path)
    monkeypatch.setattr("config.paths.DB_PATH", db_file)
    monkeypatch.setattr("db.database.DATA_DIR", tmp_path)
    monkeypatch.setattr("db.database.DB_PATH", db_file)
    monkeypatch.setattr("db.database._engine", None)
    monkeypatch.setattr("db.database._SessionLocal", None)
    init_db()


def test_admin_lists_all_accounts(tmp_path, monkeypatch) -> None:
    _setup_db(tmp_path, monkeypatch)
    user_a = UserRepository().create(
        name="Alice",
        email="alice@hist.local",
        password="secret12345",
    )
    user_b = UserRepository().create(
        name="Bob",
        email="bob@hist.local",
        password="secret12345",
    )
    ArticleRepository(user_id=user_a.id).create(
        title="A",
        markdown_content="# A",
        user_id=user_a.id,
    )
    ArticleRepository(user_id=user_b.id).create(
        title="B",
        markdown_content="# B",
        user_id=user_b.id,
    )

    records = history_list_records(
        session_user_id=user_a.id,
        is_admin=True,
        scope_user_id=HISTORY_SCOPE_ALL,
    )
    assert {r.title for r in records} == {"A", "B"}

    filtered = history_list_records(
        session_user_id=user_a.id,
        is_admin=True,
        scope_user_id=user_b.id,
    )
    assert [r.title for r in filtered] == ["B"]


def test_regular_user_only_own_history(tmp_path, monkeypatch) -> None:
    _setup_db(tmp_path, monkeypatch)
    user_a = UserRepository().create(
        name="Alice",
        email="alice2@hist.local",
        password="secret12345",
    )
    user_b = UserRepository().create(
        name="Bob",
        email="bob2@hist.local",
        password="secret12345",
    )
    ArticleRepository(user_id=user_a.id).create(
        title="A",
        markdown_content="# A",
        user_id=user_a.id,
    )
    ArticleRepository(user_id=user_b.id).create(
        title="B",
        markdown_content="# B",
        user_id=user_b.id,
    )

    records = history_list_records(
        session_user_id=user_a.id,
        is_admin=False,
        scope_user_id=HISTORY_SCOPE_ALL,
    )
    assert [r.title for r in records] == ["A"]


def test_user_cannot_see_admin_history(tmp_path, monkeypatch) -> None:
    _setup_db(tmp_path, monkeypatch)
    admin = UserRepository().create(
        name="Admin",
        email="admin@hist.local",
        password="secret12345",
    )
    assert admin.role == UserRole.ADMIN.value
    user = UserRepository().create(
        name="Maria",
        email="maria@hist.local",
        password="secret12345",
    )
    admin_article = ArticleRepository(user_id=admin.id).create(
        title="Só admin",
        markdown_content="# admin",
        user_id=admin.id,
    )
    ArticleRepository(user_id=user.id).create(
        title="Maria",
        markdown_content="# maria",
        user_id=user.id,
    )

    records = history_list_records(
        session_user_id=user.id,
        is_admin=False,
        scope_user_id=HISTORY_SCOPE_ALL,
    )
    assert [r.title for r in records] == ["Maria"]
    assert not record_accessible(
        admin_article,
        session_user_id=user.id,
        is_admin=False,
    )


def test_history_import_by_username(tmp_path, monkeypatch) -> None:
    _setup_db(tmp_path, monkeypatch)
    UserRepository().create(
        name="Admin",
        email="admin@hist.local",
        password="secret12345",
    )
    user = UserRepository().create(
        name="Bruno",
        email="bruno@hist.local",
        password="secret12345",
    )
    owner_id, err = history_import_owner_id(
        is_admin=True,
        scope_user_id=HISTORY_SCOPE_ALL,
        session_user_id=1,
        import_username="Bruno",
    )
    assert err is None
    assert owner_id == user.id

    missing, err2 = history_import_owner_id(
        is_admin=True,
        scope_user_id=HISTORY_SCOPE_ALL,
        session_user_id=1,
        import_username="Inexistente",
    )
    assert missing is None
    assert err2


def test_resolve_user_by_name_case_insensitive(tmp_path, monkeypatch) -> None:
    _setup_db(tmp_path, monkeypatch)
    UserRepository().create(
        name="Alice",
        email="alice@hist.local",
        password="secret12345",
    )
    user, err = resolve_user_by_name("alice")
    assert err is None
    assert user is not None
    assert user.name == "Alice"


def test_history_write_user_id_for_admin_filtered_account(
    tmp_path,
    monkeypatch,
) -> None:
    _setup_db(tmp_path, monkeypatch)
    admin = UserRepository().create(
        name="Admin",
        email="admin2@hist.local",
        password="secret12345",
    )
    user = UserRepository().create(
        name="U",
        email="user@hist.local",
        password="secret12345",
    )
    owner = history_write_user_id(
        session_user_id=admin.id,
        is_admin=True,
        scope_user_id=user.id,
    )
    assert owner == user.id
    assert (
        history_stats_user_id(
            session_user_id=admin.id,
            is_admin=True,
            scope_user_id=HISTORY_SCOPE_ALL,
        )
        is None
    )


def test_sort_drafts_first() -> None:
    older = ArticleRecord(
        id=1,
        title="Old done",
        markdown_content="#",
        json_index=None,
        status=ArticleStatus.COMPLETED.value,
        created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
    )
    draft_new = ArticleRecord(
        id=2,
        title="Draft",
        markdown_content="#",
        json_index=None,
        status=ArticleStatus.DRAFT.value,
        created_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
    )
    ordered = sort_history_records([older, draft_new])
    assert [r.id for r in ordered] == [2, 1]


def test_filter_drafts_only_and_count() -> None:
    draft = ArticleRecord(
        id=1,
        title="D",
        markdown_content="#",
        json_index=None,
        status=ArticleStatus.DRAFT.value,
        created_at=datetime.now(timezone.utc),
    )
    done = ArticleRecord(
        id=2,
        title="C",
        markdown_content="#",
        json_index=None,
        status=ArticleStatus.COMPLETED.value,
        created_at=datetime.now(timezone.utc),
    )
    assert len(filter_drafts_only([draft, done], enabled=True)) == 1
    assert count_drafts({"draft": 2, "completed": 5}) == 2
