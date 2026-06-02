"""Testes de fallback HTTP → navegador headless."""

from __future__ import annotations

import pytest

from services.article_fetcher import FetchedArticle, _fetch_article_live


def _thin_http(url: str, domain: str) -> FetchedArticle:
    return FetchedArticle(
        url=url,
        domain=domain,
        title="",
        text="curto",
        headings=[],
        fetch_method="http",
    )


def _rich_browser(url: str, domain: str) -> FetchedArticle:
    return FetchedArticle(
        url=url,
        domain=domain,
        title="Título JS",
        text="Conteúdo renderizado " * 40,
        headings=["H1"],
        fetch_method="browser",
    )


def test_browser_fallback_when_http_thin(monkeypatch) -> None:
    url = "https://example.com/spa"
    domain = "example.com"
    monkeypatch.setenv("GEO_BROWSER_FETCH", "auto")
    monkeypatch.setattr(
        "services.article_fetcher._fetch_article_http",
        _thin_http,
    )
    monkeypatch.setattr(
        "services.article_fetcher.is_playwright_installed",
        lambda: True,
    )
    monkeypatch.setattr(
        "services.article_fetcher._fetch_article_browser",
        _rich_browser,
    )

    article = _fetch_article_live(url, domain)
    assert article.fetch_method == "browser"
    assert "renderizado" in article.text


def test_http_kept_when_browser_disabled(monkeypatch) -> None:
    url = "https://example.com/page"
    domain = "example.com"
    monkeypatch.setenv("GEO_BROWSER_FETCH", "never")
    monkeypatch.setattr(
        "services.article_fetcher._fetch_article_http",
        _thin_http,
    )

    article = _fetch_article_live(url, domain)
    assert article.fetch_method == "http"
    assert article.text == "curto"
