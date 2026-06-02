"""Rota /dashboard."""

from __future__ import annotations

from nicegui import ui

from ui.pages.routes import ROUTE_DASHBOARD
from ui.pages.shell import render_page
from ui.tab_dashboard import build_tab_dashboard


def register(config) -> None:
    @ui.page(ROUTE_DASHBOARD)
    def dashboard_page() -> None:
        render_page(config, ROUTE_DASHBOARD, build_tab_dashboard)
