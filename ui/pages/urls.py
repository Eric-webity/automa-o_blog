"""Rota /urls."""

from __future__ import annotations

from nicegui import ui

from ui.pages.routes import ROUTE_URLS
from ui.pages.shell import render_page
from ui.tab_urls import build_tab_urls


def register(config) -> None:
    @ui.page(ROUTE_URLS)
    def urls_page() -> None:
        render_page(config, ROUTE_URLS, build_tab_urls)
