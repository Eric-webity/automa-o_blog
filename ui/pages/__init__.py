"""Páginas roteadas do Content Studio (uma URL por página)."""

from __future__ import annotations


def register_pages(config) -> None:
    """Registra todas as rotas (@ui.page) capturando o ``config`` compartilhado.

    Os módulos de página são importados aqui dentro (e não no topo) para manter
    o pacote leve e evitar ciclos de importação com ``ui.state``.
    """
    from nicegui import ui

    from ui.auth import is_authenticated
    from ui.pages import (
        admin,
        auth_pages,
        batch,
        blog,
        dashboard,
        history,
        json_page,
        profile,
        settings,
        text,
        urls,
    )
    from ui.pages.routes import ROUTE_DASHBOARD, ROUTE_HOME, ROUTE_LOGIN

    auth_pages.register(config)
    dashboard.register(config)
    blog.register(config)
    batch.register(config)
    urls.register(config)
    text.register(config)
    json_page.register(config)
    history.register(config)
    profile.register(config)
    admin.register(config)
    settings.register(config)

    @ui.page(ROUTE_HOME)
    def home_page() -> None:
        ui.navigate.to(ROUTE_DASHBOARD if is_authenticated() else ROUTE_LOGIN)
