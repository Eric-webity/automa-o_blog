"""Testes de validação de URLs na API REST."""

from __future__ import annotations

import pytest
from starlette.testclient import TestClient

from api.routes import create_api_app
from db.database import init_db


@pytest.fixture
def api_client(tmp_path, monkeypatch):
    db_file = tmp_path / "api_url_test.db"
    monkeypatch.setattr("config.paths.DATA_DIR", tmp_path)
    monkeypatch.setattr("config.paths.DB_PATH", db_file)
    monkeypatch.setattr("db.database.DATA_DIR", tmp_path)
    monkeypatch.setattr("db.database.DB_PATH", db_file)
    monkeypatch.setattr("db.database._engine", None)
    monkeypatch.setattr("db.database._SessionLocal", None)
    monkeypatch.setenv("GEO_ENV", "development")
    monkeypatch.setenv("GEO_API_ENABLED", "true")
    monkeypatch.delenv("GEO_API_KEY", raising=False)
    init_db()
    with TestClient(create_api_app()) as client:
        yield client


def test_generate_rejects_localhost_url(api_client: TestClient) -> None:
    response = api_client.post(
        "/api/v1/articles/generate",
        json={
            "topic": "Teste SSRF na API",
            "reference_urls": ["http://localhost/admin"],
            "use_llm": False,
            "save_to_db": False,
            "notify_webhook": False,
        },
    )
    assert response.status_code == 422


def test_generate_rejects_private_ip_url(api_client: TestClient) -> None:
    response = api_client.post(
        "/api/v1/articles/generate",
        json={
            "topic": "Teste SSRF IP privado",
            "reference_urls": ["http://192.168.0.1/internal"],
            "use_llm": False,
            "save_to_db": False,
            "notify_webhook": False,
        },
    )
    assert response.status_code == 422
