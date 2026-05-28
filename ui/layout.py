"""Content Studio: sidebar + área principal em cartões."""

from __future__ import annotations

from nicegui import ui

from config.paths import UI_STYLE_PATH

from ui.tab_blog import build_tab_blog
from ui.tab_dashboard import build_tab_dashboard
from ui.tab_history import build_tab_history
from ui.tab_json import build_tab_json
from ui.tab_settings import build_tab_settings
from ui.tab_text import build_tab_text
from ui.tab_urls import build_tab_urls

def apply_styles() -> None:
    """Carrega folha de estilos global do Content Studio."""
    css = UI_STYLE_PATH.read_text(encoding="utf-8") if UI_STYLE_PATH.is_file() else ""
    ui.add_head_html(f"<style>{css}</style>")


def _config_panel(config) -> None:
    """Toggles e provedor na base da sidebar."""
    switch_refs: dict[str, ui.switch] = {}

    def on_advanced(_) -> None:
        config.use_advanced = bool(switch_refs["advanced"].value)

    with ui.element("div").classes("geo-toggle-row"):
        ui.label("Extração avançada").classes("geo-toggle-row__label")
        switch_refs["advanced"] = ui.switch(value=config.use_advanced).props(
            "dense color=primary"
        )
        switch_refs["advanced"].on("update:model-value", on_advanced)

    ready = config.ready_providers or []
    provider_options = ["auto"] + ready if ready else ["auto"]
    provider_select = (
        ui.select(provider_options, value="auto", label="Provedor de IA")
        .classes("w-full")
        .props("outlined dense")
    )

    def update_provider_state() -> None:
        if config.use_llm:
            provider_select.enable()
        else:
            provider_select.disable()

    def on_llm(_) -> None:
        config.use_llm = bool(switch_refs["llm"].value)
        update_provider_state()

    with ui.element("div").classes("geo-toggle-row"):
        ui.label("Gerar artigo com IA").classes("geo-toggle-row__label")
        switch_refs["llm"] = ui.switch(value=config.use_llm).props("dense color=primary")
        switch_refs["llm"].on("update:model-value", on_llm)

    update_provider_state()

    provider_select.on(
        "update:model-value",
        lambda e: setattr(config, "provider", None if e.value == "auto" else e.value),
    )

    if config.use_llm and not ready:
        ui.label("Configure IA na aba «Configuração IA»").classes(
            "geo-meta-caption text-orange-8 mt-2"
        )


def render_content_studio(config) -> None:
    """Layout com sidebar 100vh e cartão principal."""
    sidebar_ref: dict = {"el": None}

    def toggle_nav() -> None:
        el = sidebar_ref["el"]
        if el:
            el.classes("side-nav-bar--collapsed", toggle="side-nav-bar--collapsed")

    with ui.element("div").classes("content-studio"):
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
                        with ui.tabs().props("vertical inline-label no-caps").classes(
                            "w-full"
                        ) as tabs:
                            t_dashboard = ui.tab("Dashboard", icon="dashboard")
                            t_blog = ui.tab("Criar matéria", icon="edit_note")
                            t_urls = ui.tab("URLs", icon="link")
                            t_text = ui.tab("Texto manual", icon="description")
                            t_json = ui.tab("JSON ChatGPT", icon="data_object")
                            t_history = ui.tab("Histórico", icon="history")
                            t_settings = ui.tab("Configuração IA", icon="settings")

                        config._tabs = tabs
                        config._tab_history = t_history
                        config._tab_blog = t_blog
                        config._tab_settings = t_settings

                with ui.element("div").classes("side-nav-bar__config"):
                    ui.label("Configuração").classes("side-nav-bar__config-title")
                    _config_panel(config)

            with ui.element("div").classes("main-workspace-outer"):
                with ui.element("main").classes("main-workspace-split"):
                    with ui.tab_panels(tabs, value=t_dashboard).classes("w-full"):
                        with ui.tab_panel(t_dashboard):
                            build_tab_dashboard(config)
                        with ui.tab_panel(t_blog):
                            build_tab_blog(config)
                        with ui.tab_panel(t_urls):
                            build_tab_urls(config)
                        with ui.tab_panel(t_text):
                            build_tab_text(config)
                        with ui.tab_panel(t_json):
                            build_tab_json()
                        with ui.tab_panel(t_history):
                            build_tab_history(config)
                        with ui.tab_panel(t_settings):
                            build_tab_settings(config)
