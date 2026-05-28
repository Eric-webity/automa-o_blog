"""Testes da API REST de produção."""

from __future__ import annotations

import pytest
from starlette.testclient import TestClient

from api.routes import create_api_app
from db.database import init_db
from db.repository import ArticleRepository


@pytest.fixture
def api_client(tmp_path, monkeypatch):
    """Cliente HTTP com BD isolada."""
    db_file = tmp_path / "api_test.db"
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


def test_health_public(api_client: TestClient) -> None:
    response = api_client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "version" in body


def test_stats_without_key_in_dev(api_client: TestClient) -> None:
    response = api_client.get("/api/v1/stats")
    assert response.status_code == 200
    data = response.json()
    assert "total_articles" in data
    assert "by_status" in data


def test_stats_requires_key_when_configured(api_client: TestClient, monkeypatch) -> None:
    monkeypatch.setenv("GEO_API_KEY", "test-secret-key")
    response = api_client.get("/api/v1/stats")
    assert response.status_code == 401

    ok = api_client.get(
        "/api/v1/stats",
        headers={"X-API-Key": "test-secret-key"},
    )
    assert ok.status_code == 200


def test_list_and_get_article(api_client: TestClient) -> None:
    record = ArticleRepository().create(title="API Test", markdown_content="# Olá")

    listed = api_client.get("/api/v1/articles")
    assert listed.status_code == 200
    items = listed.json()
    assert any(item["id"] == record.id for item in items)

    detail = api_client.get(f"/api/v1/articles/{record.id}")
    assert detail.status_code == 200
    assert detail.json()["title"] == "API Test"
    assert "# Olá" in detail.json()["markdown_content"]


def test_delete_article(api_client: TestClient) -> None:
    record = ArticleRepository().create(title="Apagar", markdown_content="x")
    response = api_client.delete(f"/api/v1/articles/{record.id}")
    assert response.status_code == 204
    assert ArticleRepository().get_by_id(record.id) is None
