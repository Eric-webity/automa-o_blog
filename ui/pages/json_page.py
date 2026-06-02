"""Rota /json (JSON ChatGPT)."""

from __future__ import annotations

from nicegui import ui

from ui.pages.routes import ROUTE_JSON
from ui.pages.shell import render_page
from ui.tab_json import build_tab_json


def register(config) -> None:
    @ui.page(ROUTE_JSON)
    def json_page() -> None:
        render_page(config, ROUTE_JSON, build_tab_json)
