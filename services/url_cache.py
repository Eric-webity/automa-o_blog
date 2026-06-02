"""Cache em disco de páginas já buscadas por URL."""

from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from dataclasses import asdict, dataclass
from pathlib import Path

from config.paths import DATA_DIR

logger = logging.getLogger(__name__)

URL_CACHE_DIR = DATA_DIR / "url_cache"
_DEFAULT_TTL_HOURS = 24.0


def _cache_ttl_seconds() -> float:
    raw = os.getenv("GEO_URL_CACHE_TTL_HOURS", str(_DEFAULT_TTL_HOURS))
    try:
        hours = float(raw)
    except ValueError:
        hours = _DEFAULT_TTL_HOURS
    return max(0.0, hours) * 3600.0


def _cache_path(normalized_url: str) -> Path:
    digest = hashlib.sha256(normalized_url.encode("utf-8")).hexdigest()[:32]
    return URL_CACHE_DIR / f"{digest}.json"


@dataclass
class CachedFetch:
    """Entrada serializável do cache."""

    url: str
    domain: str
    title: str
    text: str
    headings: list[str]
    fetched_at: float
    error: str | None = None


def get_cached(url: str) -> CachedFetch | None:
    """Devolve artigo em cache se ainda válido."""
    if _cache_ttl_seconds() <= 0:
        return None
    path = _cache_path(url)
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        entry = CachedFetch(**data)
    except (json.JSONDecodeError, TypeError, OSError) as exc:
        logger.debug("Cache inválido para %s: %s", url, exc)
        return None
    if entry.error:
        return None
    age = time.time() - entry.fetched_at
    if age > _cache_ttl_seconds():
        return None
    return entry


def set_cached(
    *,
    url: str,
    domain: str,
    title: str,
    text: str,
    headings: list[str],
    error: str | None = None,
) -> None:
    """Grava fetch bem-sucedido no cache."""
    if error or _cache_ttl_seconds() <= 0:
        return
    try:
        URL_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        entry = CachedFetch(
            url=url,
            domain=domain,
            title=title,
            text=text,
            headings=headings,
            fetched_at=time.time(),
            error=None,
        )
        _cache_path(url).write_text(
            json.dumps(asdict(entry), ensure_ascii=False),
            encoding="utf-8",
        )
    except OSError as exc:
        logger.warning("Não foi possível gravar cache de URL: %s", exc)


def is_cache_enabled() -> bool:
    """False quando TTL é 0 (cache desativado)."""
    return _cache_ttl_seconds() > 0


def cache_ttl_hours() -> float:
    raw = os.getenv("GEO_URL_CACHE_TTL_HOURS", str(_DEFAULT_TTL_HOURS))
    try:
        return max(0.0, float(raw))
    except ValueError:
        return _DEFAULT_TTL_HOURS


def count_cached_urls(normalized_urls: list[str]) -> int:
    """Quantas URLs já têm entrada válida em cache (sem fazer HTTP)."""
    if not is_cache_enabled():
        return 0
    return sum(1 for url in normalized_urls if get_cached(url) is not None)


def cache_file_count() -> int:
    if not URL_CACHE_DIR.is_dir():
        return 0
    return len(list(URL_CACHE_DIR.glob("*.json")))


def clear_url_cache() -> int:
    """Remove todos os ficheiros de cache. Devolve quantidade apagada."""
    if not URL_CACHE_DIR.is_dir():
        return 0
    count = 0
    for path in URL_CACHE_DIR.glob("*.json"):
        try:
            path.unlink()
            count += 1
        except OSError:
            pass
    return count
