"""Painel de validação do formulário antes de gerar matéria."""

from __future__ import annotations

from collections.abc import Callable

from nicegui import ui

from services.article_validation import evaluate_brief_preflight
from services.blog import parse_keywords
from ui.constants import blog_word_count


def render_brief_preflight(
    *,
    topic_getter: Callable[[], str],
    keywords_getter: Callable[[], str],
    refs_getter: Callable[[], str],
    word_count_getter: Callable[[], str],
    use_llm: bool,
    host: ui.element,
) -> None:
    """Atualiza checklist «Antes de gerar» no painel lateral."""
    host.clear()
    items = evaluate_brief_preflight(
        topic=topic_getter(),
        keywords=parse_keywords(keywords_getter() or ""),
        reference_urls=[
            u.strip() for u in (refs_getter() or "").splitlines() if u.strip()
        ],
        word_count=blog_word_count(word_count_getter()),
        use_llm=use_llm,
    )
    ok = sum(1 for i in items if i.passed)

    with host:
        with ui.expansion(
            f"Antes de gerar ({ok}/{len(items)} OK)",
            icon="playlist_add_check",
        ).classes("geo-preflight-panel w-full").props("dense"):
            ui.label(
                "Confira o briefing antes de gastar tokens. Itens em falha podem "
                "impedir ou prejudicar a geração."
            ).classes("geo-preflight__intro")

            for item in items:
                icon = "check_circle" if item.passed else "error_outline"
                color = "positive" if item.passed else "warning"
                row_cls = (
                    "geo-preflight__row geo-preflight__row--ok"
                    if item.passed
                    else "geo-preflight__row geo-preflight__row--pending"
                )
                with ui.element("div").classes(row_cls):
                    with ui.row().classes("items-start gap-2 w-full"):
                        ui.icon(icon, color=color).classes("geo-preflight__icon")
                        with ui.column().classes("gap-0 flex-grow min-w-0"):
                            ui.label(item.label).classes("geo-preflight__label")
                            if item.detail:
                                ui.label(item.detail).classes("geo-meta-caption")
                            if not item.passed and item.hint:
                                ui.label(item.hint).classes("geo-preflight__hint")
