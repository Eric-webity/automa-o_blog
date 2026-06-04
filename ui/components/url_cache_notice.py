"""Avisos de cache de URLs na interface."""

from __future__ import annotations

from nicegui import ui

from services.article_fetcher import UrlFetchStats
from services.url_cache import cache_ttl_hours, is_cache_enabled


def render_url_cache_banner(message: str | None) -> bool:
    """Banner informativo quando referências vieram do cache local."""
    if not message or not is_cache_enabled():
        return False
    with ui.element("div").classes("geo-url-cache-banner w-full mb-4"):
        with ui.row().classes("items-start gap-3 w-full"):
            ui.icon("cached", color="primary").classes("mt-0.5")
            with ui.column().classes("gap-1 flex-grow"):
                ui.label("Referências em cache").classes("geo-url-cache-banner__title")
                ui.label(message).classes("geo-url-cache-banner__text")
                ui.label(
                    f"Páginas guardadas em disco por até {int(cache_ttl_hours())}h "
                    "(GEO_URL_CACHE_TTL_HOURS)."
                ).classes("geo-meta-caption")
    return True


def render_url_cache_chip(stats: UrlFetchStats) -> None:
    """Chip compacto após fetch de URLs."""
    if stats.cache_hits <= 0 or not is_cache_enabled():
        return
    ui.html(
        f'<span class="geo-chip geo-chip--primary">'
        f"{stats.cache_hits} URL(s) do cache</span>"
    )
