"""Rota /admin — painel de administração (acesso restrito)."""

from __future__ import annotations

from nicegui import ui

from ui.auth import is_admin, is_authenticated
from ui.layout import apply_styles
from ui.pages.routes import ROUTE_LOGIN, ROUTE_PROFILE
from ui.pages.shell import render_page
from ui.tab_profile_admin import build_tab_profile_admin


def register(config) -> None:
    from ui.pages.routes import ROUTE_ADMIN

    @ui.page(ROUTE_ADMIN)
    def admin_page() -> None:
        apply_styles()
        if not is_authenticated():
            ui.navigate.to(ROUTE_LOGIN)
            return
        if not is_admin():
            ui.notify("Acesso restrito a administradores.", type="warning")
            ui.navigate.to(ROUTE_PROFILE)
            return
        render_page(config, ROUTE_ADMIN, build_tab_profile_admin)
