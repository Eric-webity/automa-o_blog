"""Rotas de autenticação: /login e /cadastro (tela cheia, sem sidebar)."""

from __future__ import annotations

from nicegui import ui

from ui.auth import is_authenticated
from ui.layout import apply_styles
from ui.pages.routes import ROUTE_DASHBOARD, ROUTE_LOGIN, ROUTE_SIGNUP
from ui.tab_login import render_login_gate
from ui.tab_signup import render_signup_gate


def register(config) -> None:
    @ui.page(ROUTE_LOGIN)
    def login_page() -> None:
        apply_styles()
        if is_authenticated():
            ui.navigate.to(ROUTE_DASHBOARD)
            return
        with ui.column().classes("geo-app-root w-full min-h-screen"):
            render_login_gate(
                config,
                on_success=lambda: ui.navigate.to(ROUTE_DASHBOARD),
                on_signup=lambda: ui.navigate.to(ROUTE_SIGNUP),
            )

    @ui.page(ROUTE_SIGNUP)
    def signup_page() -> None:
        apply_styles()
        if is_authenticated():
            ui.navigate.to(ROUTE_DASHBOARD)
            return
        with ui.column().classes("geo-app-root w-full min-h-screen"):
            render_signup_gate(
                config,
                on_success=lambda: ui.navigate.to(ROUTE_DASHBOARD),
                on_login=lambda: ui.navigate.to(ROUTE_LOGIN),
            )
