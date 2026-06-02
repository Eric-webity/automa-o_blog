"""Rota /texto."""

from __future__ import annotations

from nicegui import ui

from ui.pages.routes import ROUTE_TEXT
from ui.pages.shell import render_page
from ui.tab_text import build_tab_text


def register(config) -> None:
    @ui.page(ROUTE_TEXT)
    def text_page() -> None:
        render_page(config, ROUTE_TEXT, build_tab_text)
