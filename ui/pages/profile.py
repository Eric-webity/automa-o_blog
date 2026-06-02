"""Rota /perfil."""

from __future__ import annotations

from nicegui import ui

from ui.pages.routes import ROUTE_PROFILE
from ui.pages.shell import render_page
from ui.tab_profile import build_tab_profile


def register(config) -> None:
    @ui.page(ROUTE_PROFILE)
    def profile_page() -> None:
        render_page(config, ROUTE_PROFILE, build_tab_profile)
