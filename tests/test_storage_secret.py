"""Validação de GEO_STORAGE_SECRET em produção."""

from __future__ import annotations

import pytest

from config.production import (
    STORAGE_SECRET_DEV_DEFAULT,
    STORAGE_SECRET_MIN_LENGTH,
    resolve_storage_secret,
)


def test_development_uses_default_when_empty(monkeypatch) -> None:
    monkeypatch.delenv("GEO_STORAGE_SECRET", raising=False)
    monkeypatch.setenv("GEO_ENV", "development")
    assert resolve_storage_secret() == STORAGE_SECRET_DEV_DEFAULT


def test_development_respects_custom_secret(monkeypatch) -> None:
    monkeypatch.setenv("GEO_STORAGE_SECRET", "my-local-secret-only-for-dev")
    monkeypatch.setenv("GEO_ENV", "development")
    assert resolve_storage_secret() == "my-local-secret-only-for-dev"


def test_production_requires_secret(monkeypatch) -> None:
    monkeypatch.delenv("GEO_STORAGE_SECRET", raising=False)
    monkeypatch.setenv("GEO_ENV", "production")
    with pytest.raises(SystemExit):
        resolve_storage_secret()


def test_production_rejects_dev_default(monkeypatch) -> None:
    monkeypatch.setenv("GEO_STORAGE_SECRET", STORAGE_SECRET_DEV_DEFAULT)
    monkeypatch.setenv("GEO_ENV", "production")
    with pytest.raises(SystemExit):
        resolve_storage_secret()


def test_production_accepts_strong_secret(monkeypatch) -> None:
    secret = "x" * STORAGE_SECRET_MIN_LENGTH
    monkeypatch.setenv("GEO_STORAGE_SECRET", secret)
    monkeypatch.setenv("GEO_ENV", "production")
    assert resolve_storage_secret() == secret
