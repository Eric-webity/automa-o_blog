"""Shell compartilhado das páginas roteadas: sidebar + área principal.

Substitui as abas client-side por navegação real entre rotas, mantendo o
mesmo visual (barra lateral, configuração e área de trabalho).
"""

from __future__ import annotations

from typing import Callable

from nicegui import ui

from ui.auth import is_authenticated, logout, session_email
from ui.layout import _config_panel, apply_styles
from ui.pages.routes import NAV_ITEMS, ROUTE_LOGIN


def render_page(config, active_path: str, builder: Callable[[object], None]) -> None:
    """Renderiza uma página protegida com o shell padrão.

    ``builder`` é chamado dentro da área principal e recebe o ``config``.
    """
    apply_styles()
    if not is_authenticated():
        ui.navigate.to(ROUTE_LOGIN)
        return
    config.handle_logout = lambda: (logout(), ui.navigate.to(ROUTE_LOGIN))
    _render_shell(config, active_path, builder)


def _render_shell(config, active_path: str, builder: Callable[[object], None]) -> None:
    sidebar_ref: dict = {"el": None}
    backdrop_ref: dict = {"el": None}

    def toggle_nav() -> None:
        el = sidebar_ref["el"]
        if el:
            el.classes("side-nav-bar--collapsed", toggle="side-nav-bar--collapsed")
            el.classes("side-nav-bar--open", toggle="side-nav-bar--open")
        backdrop = backdrop_ref.get("el")
        if backdrop:
            backdrop.classes(
                "geo-sidebar-backdrop--visible",
                toggle="geo-sidebar-backdrop--visible",
            )

    def close_mobile_nav() -> None:
        el = sidebar_ref["el"]
        if el and el.classes("side-nav-bar--open"):
            toggle_nav()

    root = ui.column().classes("geo-app-root w-full min-h-screen")
    with root:
        with ui.element("div").classes("content-studio"):
            backdrop_ref["el"] = (
                ui.element("div")
                .classes("geo-sidebar-backdrop")
                .on("click", close_mobile_nav)
            )
            with ui.element("div").classes("app-shell"):
                sidebar_ref["el"] = ui.element("aside").classes("side-nav-bar")
                with sidebar_ref["el"]:
                    with ui.element("div").classes("side-nav-bar__brand"):
                        ui.button(icon="menu", on_click=toggle_nav).props(
                            "flat round dense"
                        ).classes("header-topnavbar__menu-btn")
                        with ui.element("div").classes("side-nav-bar__brand-row"):
                            ui.label("GEO Extractor").classes("side-nav-bar__title")
                            ui.html('<span class="geo-badge">Content Studio</span>')

                    with ui.element("div").classes("side-nav-bar__nav-wrap"):
                        with ui.element("nav").classes("side-nav-bar__nav"):
                            _render_nav(active_path)

                    with ui.element("div").classes("side-nav-bar__config"):
                        ui.label("Configuração").classes("side-nav-bar__config-title")
                        _config_panel(config)
                        user_email = session_email()
                        if user_email:
                            ui.label(user_email).classes("geo-meta-caption mt-3 truncate")
                        ui.button(
                            "Sair", icon="logout", on_click=config.handle_logout
                        ).props("flat no-caps dense color=primary").classes(
                            "self-start mt-2"
                        )

                with ui.element("div").classes("main-workspace-outer"):
                    with ui.element("main").classes("main-workspace-split"):
                        builder(config)


def _render_nav(active_path: str) -> None:
    """Barra de navegação vertical que troca de rota ao clicar."""
    active_label = next(
        (label for path, label, _ in NAV_ITEMS if path == active_path), None
    )
    with ui.tabs(value=active_label).props("vertical inline-label no-caps").classes(
        "w-full"
    ) as tabs:
        for _path, label, icon in NAV_ITEMS:
            ui.tab(label, icon=icon)

    label_to_path = {label: path for path, label, _ in NAV_ITEMS}

    def on_change(event) -> None:
        target = label_to_path.get(event.value)
        if target and target != active_path:
            ui.navigate.to(target)

    tabs.on_value_change(on_change)
