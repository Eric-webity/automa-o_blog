"""Banner de aviso quando a extensão fica abaixo da meta."""

from __future__ import annotations

from nicegui import ui

from services.word_count import (
    WORD_COUNT_WARNING_RATIO,
    build_word_count_warning,
    is_below_word_count_target,
    word_count_ratio,
)
from ui.constants import ALERT_WARNING


def render_word_count_banner(
    *,
    actual: int,
    target: int,
    warning: str | None = None,
) -> bool:
    """
    Mostra banner destacado se actual < 85% da meta.

    Devolve True se o aviso foi exibido.
    """
    if not is_below_word_count_target(actual, target):
        return False

    message = warning or build_word_count_warning(actual, target) or ""
    ratio = word_count_ratio(actual, target)
    pct = int((ratio or 0) * 100)

    with ui.element("div").classes("geo-word-count-banner w-full mb-4"):
        with ui.row().classes("items-start gap-3 w-full"):
            ui.icon("warning_amber", color="orange").classes("mt-0.5")
            with ui.column().classes("gap-1 flex-grow"):
                ui.label("Extensão abaixo do pedido — revise antes de publicar").classes(
                    "geo-word-count-banner__title"
                )
                ui.label(message).classes("geo-word-count-banner__text")
                ui.label(
                    f"Meta: {target:,} palavras · Gerado: {actual:,} ({pct}% da meta; "
                    f"mínimo recomendado: {int(WORD_COUNT_WARNING_RATIO * 100)}%)"
                ).classes("geo-meta-caption")
    return True


def notify_word_count_if_needed(*, actual: int, target: int, warning: str | None = None) -> None:
    """Notificação toast quando a extensão fica abaixo da meta."""
    if not is_below_word_count_target(actual, target):
        return
    msg = warning or build_word_count_warning(actual, target)
    if msg:
        ui.notify(msg, type="warning", multi_line=True, timeout=8000)
