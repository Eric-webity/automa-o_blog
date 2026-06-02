"""Rota /configuracoes (Settings)."""

from __future__ import annotations

from nicegui import ui

from ui.pages.routes import ROUTE_SETTINGS
from ui.pages.shell import render_page
from ui.tab_settings import build_tab_settings


def register(config) -> None:
    @ui.page(ROUTE_SETTINGS)
    def settings_page() -> None:
        render_page(config, ROUTE_SETTINGS, build_tab_settings)
