"""Testes do cache de URLs."""

from __future__ import annotations

import time

import pytest

from services.url_cache import get_cached, set_cached


@pytest.fixture
def cache_dir(tmp_path, monkeypatch):
    monkeypatch.setattr("services.url_cache.URL_CACHE_DIR", tmp_path / "url_cache")
    monkeypatch.setattr("services.url_cache.DATA_DIR", tmp_path)
    monkeypatch.setenv("GEO_URL_CACHE_TTL_HOURS", "1")
    return tmp_path / "url_cache"


def test_set_and_get_cached(cache_dir) -> None:
    set_cached(
        url="https://example.com/post",
        domain="example.com",
        title="Título",
        text="Texto longo " * 20,
        headings=["H1"],
    )
    entry = get_cached("https://example.com/post")
    assert entry is not None
    assert entry.title == "Título"
    assert entry.text.startswith("Texto longo")


def test_cache_expires(cache_dir, monkeypatch) -> None:
    monkeypatch.setenv("GEO_URL_CACHE_TTL_HOURS", "0.0001")
    set_cached(
        url="https://example.com/old",
        domain="example.com",
        title="Old",
        text="x" * 100,
        headings=[],
    )
    time.sleep(0.5)
    assert get_cached("https://example.com/old") is None
