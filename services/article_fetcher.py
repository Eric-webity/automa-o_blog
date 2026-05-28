"""Extração de conteúdo a partir de URLs de matérias."""

from __future__ import annotations

import ipaddress
import re
import socket
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

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
class FetchedArticle:
    url: str
    domain: str
    title: str
    text: str
    headings: list[str]
    error: str | None = None


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

    domain = _domain(url)
    try:
        resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
            tag.decompose()

        title = ""
        if soup.title and soup.title.string:
            title = soup.title.string.strip()
        h1 = soup.find("h1")
        if h1:
            title = h1.get_text(strip=True) or title

        headings = [
            h.get_text(strip=True)
            for h in soup.find_all(["h1", "h2", "h3"])
            if h.get_text(strip=True)
        ][:12]

        paragraphs = [
            p.get_text(strip=True)
            for p in soup.find_all("p")
            if len(p.get_text(strip=True)) > 40
        ]
        text = "\n\n".join(paragraphs)
        if not text:
            text = soup.get_text(separator="\n", strip=True)
        text = re.sub(r"\n{3,}", "\n\n", text)[:25_000]

        return FetchedArticle(
            url=url,
            domain=domain,
            title=title or domain,
            text=text,
            headings=headings,
        )
    except Exception as e:
        return FetchedArticle(
            url=url,
            domain=domain,
            title="",
            text="",
            headings=[],
            error=str(e),
        )


def fetch_many(urls: list[str], max_workers: int = MAX_WORKERS) -> list[FetchedArticle]:
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

    if not unique:
        return []

    if len(unique) == 1:
        return [fetch_article(unique[0])]

    results: dict[str, FetchedArticle] = {}
    with ThreadPoolExecutor(max_workers=min(max_workers, len(unique))) as pool:
        futures = {pool.submit(fetch_article, u): u for u in unique}
        for future in as_completed(futures):
            art = future.result()
            results[art.url] = art

    return [results[u] for u in unique if u in results]
