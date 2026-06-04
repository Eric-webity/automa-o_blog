"""Testes de papéis de utilizador (user / admin)."""

from __future__ import annotations

import pytest

from db.database import init_db
from db.models import UserRole
from db.repository import UserRepository


@pytest.fixture(autouse=True)
def _fresh_db(tmp_path, monkeypatch):
    db_file = tmp_path / "test.db"
    monkeypatch.setattr("config.paths.DATA_DIR", tmp_path)
    monkeypatch.setattr("config.paths.DB_PATH", db_file)
    monkeypatch.setattr("db.database.DATA_DIR", tmp_path)
    monkeypatch.setattr("db.database.DB_PATH", db_file)
    from db import database as db_mod

    db_mod._engine = None
    db_mod._SessionLocal = None
    init_db()
    yield
    db_mod._engine = None
    db_mod._SessionLocal = None


def test_first_user_is_admin() -> None:
    user = UserRepository().create(
        name="Admin",
        email="admin@test.com",
        password="senha12345",
    )
    assert user.role == UserRole.ADMIN.value


def test_second_user_is_regular() -> None:
    UserRepository().create(name="A", email="a@test.com", password="senha12345")
    user = UserRepository().create(name="B", email="b@test.com", password="senha12345")
    assert user.role == UserRole.USER.value


def test_cannot_demote_last_admin() -> None:
    admin = UserRepository().create(name="A", email="a@test.com", password="senha12345")
    with pytest.raises(ValueError, match="último administrador"):
        UserRepository().set_role(admin.id, UserRole.USER.value)


def test_promote_user_to_admin() -> None:
    UserRepository().create(name="A", email="a@test.com", password="senha12345")
    user = UserRepository().create(name="B", email="b@test.com", password="senha12345")
    updated = UserRepository().set_role(user.id, UserRole.ADMIN.value)
    assert updated.role == UserRole.ADMIN.value
