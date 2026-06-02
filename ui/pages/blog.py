"""Rota /criar-materia."""

from __future__ import annotations

from nicegui import ui

from ui.pages.routes import ROUTE_BLOG
from ui.pages.shell import render_page
from ui.tab_blog import build_tab_blog


def register(config) -> None:
    @ui.page(ROUTE_BLOG)
    def blog_page() -> None:
        render_page(config, ROUTE_BLOG, build_tab_blog)
