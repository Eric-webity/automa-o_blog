"""Content Studio: estilos globais e painel de configuração da sidebar.

A montagem da casca (sidebar + área principal) e a navegação por rotas ficam
em ``ui/pages/`` (uma URL por página). Este módulo mantém apenas os utilitários
compartilhados: ``apply_styles`` e ``_config_panel``.
"""

from __future__ import annotations

from nicegui import ui

from config.paths import UI_DESIGN_TOKENS_PATH, UI_STYLE_PATH

from ui.constants import provider_select_options


def apply_styles() -> None:
    """Carrega folha de estilos global do Content Studio."""
    tokens = (
        UI_DESIGN_TOKENS_PATH.read_text(encoding="utf-8")
        if UI_DESIGN_TOKENS_PATH.is_file()
        else ""
    )
    css = UI_STYLE_PATH.read_text(encoding="utf-8") if UI_STYLE_PATH.is_file() else ""
    ui.add_head_html(
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        '<link rel="preconnect" href="https://fonts.googleapis.com">'
        '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
        '<link href="https://fonts.googleapis.com/css2?family=Manrope:wght@400;600;700;800&display=swap" rel="stylesheet">'
        '<link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@24,400,0,0" rel="stylesheet">'
        f"<style>{tokens}\n{css}</style>"
    )


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
    provider_options = provider_select_options(ready)
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
        switch_refs["llm"] = ui.switch(value=config.use_llm).props(
            "dense color=primary"
        )
        switch_refs["llm"].on("update:model-value", on_llm)

    update_provider_state()

    provider_select.on(
        "update:model-value",
        lambda e: setattr(config, "provider", None if e.value == "auto" else e.value),
    )

    if config.use_llm and not ready:
        ui.label("Configure IA na página «Settings»").classes(
            "geo-meta-caption text-orange-8 mt-2"
        )
