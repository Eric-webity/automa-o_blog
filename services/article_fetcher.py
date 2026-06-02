"""Extração de conteúdo a partir de URLs de matérias."""

from __future__ import annotations

import ipaddress
import logging
import re
import socket
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from urllib.parse import urlparse

import requests

from services.browser_fetcher import (
    browser_fetch_enabled,
    browser_fetch_mode,
    fetch_page_html,
    is_playwright_installed,
    min_text_for_http,
)
from services.html_extract import parse_html
from services.url_cache import cache_ttl_hours, get_cached, is_cache_enabled, set_cached

logger = logging.getLogger(__name__)

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
TIMEOUT = 15
MAX_WORKERS = 5

_BLOCKED_HOST_RE = re.compile(
    r"^(localhost|127\.\d+\.\d+\.\d+|0\.0\.0\.0|::1|169\.254\.\d+\.\d+|"
    r"10\.\d+\.\d+\.\d+|192\.168\.\d+\.\d+|172\.(1[6-9]|2\d|3[01])\.\d+\.\d+)$",
    re.I,
)


class URLValidationError(ValueError):
    """URL rejeitada por política de segurança."""


@dataclass
class UrlFetchStats:
    """Resumo de uso do cache de URLs num lote."""

    cache_hits: int = 0
    cache_misses: int = 0
    browser_fetches: int = 0

    @property
    def total(self) -> int:
        return self.cache_hits + self.cache_misses

    def summary_message(self) -> str:
        if self.total == 0:
            return ""
        if not is_cache_enabled():
            return "Cache de URLs desativado (GEO_URL_CACHE_TTL_HOURS=0)."
        base = ""
        if self.cache_hits == self.total:
            base = (
                f"Referências: {self.cache_hits} URL(s) lidas do cache local "
                "(sem novo download)."
            )
        elif self.cache_hits == 0:
            base = (
                f"Referências: {self.cache_misses} URL(s) buscadas na web "
                f"(guardadas em cache por {int(cache_ttl_hours())}h)."
            )
        else:
            base = (
                f"Referências: {self.cache_hits} do cache, {self.cache_misses} nova(s) na web "
                f"(TTL {int(cache_ttl_hours())}h)."
            )
        if self.browser_fetches:
            base += f" · {self.browser_fetches} via navegador headless (JS)."
        return base


@dataclass
class FetchedArticle:
    url: str
    domain: str
    title: str
    text: str
    headings: list[str]
    error: str | None = None
    from_cache: bool = False
    fetch_method: str = "http"  # http | browser | cache


def _domain(url: str) -> str:
    return urlparse(url).netloc.replace("www.", "")


def _normalize_url(raw: str) -> str:
    u = raw.strip()
    if not u.startswith(("http://", "https://")):
        u = "https://" + u
    return u


def _is_private_ip(host: str) -> bool:
    try:
        for info in socket.getaddrinfo(host, None):
            ip = ipaddress.ip_address(info[4][0])
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
                return True
    except (socket.gaierror, ValueError, OSError):
        pass
    return False


def validate_url(url: str) -> str:
    """Valida URL e retorna versão normalizada. Levanta URLValidationError se bloqueada."""
    normalized = _normalize_url(url)
    parsed = urlparse(normalized)
    if parsed.scheme not in ("http", "https"):
        raise URLValidationError(f"Esquema não permitido: {parsed.scheme}")
    host = (parsed.hostname or "").lower()
    if not host:
        raise URLValidationError("URL sem hostname")
    if _BLOCKED_HOST_RE.match(host):
        raise URLValidationError(f"URL bloqueada (SSRF): {host}")
    if _is_private_ip(host):
        raise URLValidationError(f"URL bloqueada (IP privado): {host}")
    return normalized


def _parsed_to_article(parsed, *, url: str, domain: str, fetch_method: str) -> FetchedArticle:
    return FetchedArticle(
        url=url,
        domain=domain,
        title=parsed.title or domain,
        text=parsed.text,
        headings=parsed.headings,
        fetch_method=fetch_method,
    )


def _text_len(article: FetchedArticle) -> int:
    return len((article.text or "").strip())


def _should_try_browser(article: FetchedArticle) -> bool:
    if not browser_fetch_enabled():
        return False
    if not is_playwright_installed():
        return False
    mode = browser_fetch_mode()
    if mode == "always":
        return True
    if article.error:
        return True
    return _text_len(article) < min_text_for_http()


def _fetch_article_browser(url: str, domain: str) -> FetchedArticle:
    try:
        html = fetch_page_html(url)
        parsed = parse_html(html, fallback_title=domain)
        article = _parsed_to_article(parsed, url=url, domain=domain, fetch_method="browser")
        if _text_len(article) < min_text_for_http():
            article.error = "Conteúdo insuficiente após renderização no navegador."
        return article
    except Exception as exc:
        logger.warning("Browser fetch falhou para %s: %s", url, exc)
        return FetchedArticle(
            url=url,
            domain=domain,
            title="",
            text="",
            headings=[],
            error=str(exc),
            fetch_method="browser",
        )


def _fetch_article_http(url: str, domain: str) -> FetchedArticle:
    try:
        resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT)
        resp.raise_for_status()
        parsed = parse_html(resp.text, fallback_title=domain)
        return _parsed_to_article(parsed, url=url, domain=domain, fetch_method="http")
    except Exception as e:
        return FetchedArticle(
            url=url,
            domain=domain,
            title="",
            text="",
            headings=[],
            error=str(e),
            fetch_method="http",
        )


def _fetch_article_live(url: str, domain: str) -> FetchedArticle:
    """HTTP primeiro; navegador headless se configurado e necessário."""
    mode = browser_fetch_mode()

    if mode == "always" and browser_fetch_enabled() and is_playwright_installed():
        return _fetch_article_browser(url, domain)

    http_article = _fetch_article_http(url, domain)
    if not _should_try_browser(http_article):
        if http_article.error and not is_playwright_installed() and browser_fetch_enabled():
            http_article.error = (
                f"{http_article.error} "
                "(instale Playwright para sites em JavaScript: "
                "pip install playwright && playwright install chromium)"
            )
        return http_article

    browser_article = _fetch_article_browser(url, domain)
    if browser_article.error and not http_article.error:
        return http_article
    if _text_len(browser_article) >= _text_len(http_article) and not browser_article.error:
        logger.info("URL fetch via browser: %s", url)
        return browser_article
    if http_article.error and browser_article.error:
        return browser_article
    return http_article


def fetch_article(url: str) -> FetchedArticle:
    try:
        url = validate_url(url)
    except URLValidationError as e:
        return FetchedArticle(
            url=url,
            domain=_domain(url) if "://" in url else "",
            title="",
            text="",
            headings=[],
            error=str(e),
        )

    cached = get_cached(url)
    if cached:
        logger.info("URL cache hit: %s", url)
        return FetchedArticle(
            url=cached.url,
            domain=cached.domain,
            title=cached.title,
            text=cached.text,
            headings=list(cached.headings),
            from_cache=True,
            fetch_method="cache",
        )

    domain = _domain(url)
    article = _fetch_article_live(url, domain)
    if not article.error:
        set_cached(
            url=article.url,
            domain=article.domain,
            title=article.title,
            text=article.text,
            headings=article.headings,
        )
    return article


def _normalize_url_list(urls: list[str]) -> list[str]:
    seen: set[str] = set()
    unique: list[str] = []
    for raw in urls:
        u = raw.strip()
        if not u:
            continue
        try:
            normalized = validate_url(u)
        except URLValidationError:
            normalized = _normalize_url(u)
        if normalized in seen:
            continue
        seen.add(normalized)
        unique.append(normalized)
    return unique


def fetch_many_with_stats(
    urls: list[str],
    max_workers: int = MAX_WORKERS,
) -> tuple[list[FetchedArticle], UrlFetchStats]:
    """Busca URLs com estatísticas de cache (hits evitam HTTP)."""
    unique = _normalize_url_list(urls)
    stats = UrlFetchStats()
    if not unique:
        return [], stats

    results: dict[str, FetchedArticle] = {}
    to_fetch: list[str] = []

    for url in unique:
        cached = get_cached(url)
        if cached:
            results[url] = FetchedArticle(
                url=cached.url,
                domain=cached.domain,
                title=cached.title,
                text=cached.text,
                headings=list(cached.headings),
                from_cache=True,
                fetch_method="cache",
            )
            stats.cache_hits += 1
            logger.info("URL cache hit: %s", url)
        else:
            to_fetch.append(url)

    def _record(art: FetchedArticle) -> None:
        if art.fetch_method == "browser":
            stats.browser_fetches += 1

    if to_fetch:
        if len(to_fetch) == 1:
            art = fetch_article(to_fetch[0])
            results[art.url] = art
            stats.cache_misses += 1
            _record(art)
        else:
            with ThreadPoolExecutor(max_workers=min(max_workers, len(to_fetch))) as pool:
                futures = {pool.submit(fetch_article, u): u for u in to_fetch}
                for future in as_completed(futures):
                    art = future.result()
                    results[art.url] = art
                    stats.cache_misses += 1
                    _record(art)

    ordered = [results[u] for u in unique if u in results]
    return ordered, stats


def fetch_many(urls: list[str], max_workers: int = MAX_WORKERS) -> list[FetchedArticle]:
    articles, _ = fetch_many_with_stats(urls, max_workers=max_workers)
    return articles
