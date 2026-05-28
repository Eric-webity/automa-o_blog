"""Componentes visuais reutilizáveis do Content Studio."""

from __future__ import annotations

from nicegui import ui


def page_header(title: str, description: str | None = None) -> None:
    """Título e descrição padronizados da área principal."""
    ui.label(title).classes("geo-page-title")
    if description:
        ui.label(description).classes("geo-page-desc")


def geo_textarea(
    label: str,
    *,
    placeholder: str = "",
    value: str = "",
    rows: int = 5,
) -> ui.textarea:
    """Textarea com borda arredondada e focus ring."""
    ui.label(label).classes("geo-field-label")
    field = (
        ui.textarea(value=value, placeholder=placeholder)
        .classes("w-full geo-field geo-field--textarea")
        .props(f"outlined autogrow rows={rows}")
    )
    return field


def geo_input(
    label: str,
    *,
    placeholder: str = "",
    value: str = "",
) -> ui.input:
    """Input com estilo moderno."""
    ui.label(label).classes("geo-field-label")
    return (
        ui.input(value=value, placeholder=placeholder)
        .classes("w-full geo-field")
        .props("outlined dense")
    )


def primary_button(
    label: str,
    on_click,
    *,
    icon: str | None = None,
) -> ui.button:
    """Botão principal sólido com hover."""
    btn = ui.button(label, on_click=on_click).classes("geo-btn-primary")
    if icon:
        btn.props(f"icon={icon}")
    return btn


def loading_status(message: str) -> ui.row:
    """Spinner + texto de carregamento."""
    with ui.row().classes("geo-loading-row items-center gap-3") as row:
        ui.spinner(size="md").classes("geo-loading-spinner")
        ui.label(message).classes("geo-loading-text")
    return row
