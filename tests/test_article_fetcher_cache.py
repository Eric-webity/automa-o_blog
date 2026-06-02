"""Testes de cache integrado no fetch de URLs."""

from __future__ import annotations

import pytest

from services.article_fetcher import FetchedArticle, UrlFetchStats, fetch_many_with_stats
from services.url_cache import get_cached, set_cached


@pytest.fixture
def cache_dir(tmp_path, monkeypatch):
    monkeypatch.setattr("services.url_cache.URL_CACHE_DIR", tmp_path / "url_cache")
    monkeypatch.setenv("GEO_URL_CACHE_TTL_HOURS", "24")
    return tmp_path / "url_cache"


def _fake_article(url: str) -> FetchedArticle:
    return FetchedArticle(
        url=url,
        domain="example.com",
        title="Título",
        text="Conteúdo " * 30,
        headings=["H1"],
    )


def test_fetch_many_uses_cache_on_second_call(cache_dir, monkeypatch) -> None:
    url = "https://example.com/article"

    monkeypatch.setattr(
        "services.article_fetcher._fetch_article_http",
        lambda u, d: _fake_article(u),
    )

    articles1, stats1 = fetch_many_with_stats([url])
    assert len(articles1) == 1
    assert stats1.cache_misses == 1
    assert stats1.cache_hits == 0
    assert not articles1[0].from_cache

    articles2, stats2 = fetch_many_with_stats([url])
    assert stats2.cache_hits == 1
    assert stats2.cache_misses == 0
    assert articles2[0].from_cache
    assert get_cached(url) is not None


def test_url_fetch_stats_summary() -> None:
    stats = UrlFetchStats(cache_hits=2, cache_misses=1)
    msg = stats.summary_message()
    assert "2 do cache" in msg
    assert "1 nova" in msg
