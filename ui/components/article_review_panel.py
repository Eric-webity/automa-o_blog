"""Painel de revisão pós-geração (validação + checklist) — blog, URLs e texto."""

from __future__ import annotations

from nicegui import ui

from services.article_validation import (
    primary_checks,
    secondary_checks,
    validate_article_markdown,
)
from services.word_count import build_word_count_warning, is_below_word_count_target
from ui.components.word_count_banner import render_word_count_banner


def _render_validation_row(item) -> None:
    icon = "check_circle" if item.passed else "error_outline"
    color = "positive" if item.passed else "warning"
    row_cls = (
        "geo-checklist__row geo-checklist__row--ok"
        if item.passed
        else "geo-checklist__row geo-checklist__row--pending"
    )
    with ui.element("div").classes(row_cls):
        with ui.row().classes("items-start gap-3 w-full"):
            ui.icon(icon, color=color).classes("geo-checklist__icon")
            with ui.column().classes("gap-0 flex-grow min-w-0"):
                ui.label(item.label).classes("geo-checklist__label")
                if item.detail:
                    ui.label(item.detail).classes("geo-checklist__detail")
                if not item.passed and item.hint:
                    ui.label(item.hint).classes("geo-checklist__hint")


def render_article_review_panel(
    markdown: str,
    *,
    target_words: int | None = None,
    include_faq: bool = True,
    meta_description: str = "",
    faq_items: list | None = None,
    word_count_warning: str | None = None,
    similarity_warning: str | None = None,
    fallback_reason: str | None = None,
    show_word_banner: bool = True,
) -> None:
    """
    Banner de extensão (se abaixo de 85% da meta) + checklist GEO essencial.
    """
    actual = len((markdown or "").split())

    if (
        show_word_banner
        and target_words
        and target_words > 0
        and is_below_word_count_target(actual, target_words)
    ):
        render_word_count_banner(
            actual=actual,
            target=target_words,
            warning=word_count_warning or build_word_count_warning(actual, target_words),
        )

    all_items = validate_article_markdown(
        markdown,
        target_words=target_words,
        include_faq=include_faq,
        meta_description=meta_description,
        faq_items=faq_items,
        similarity_warning=similarity_warning,
        fallback_reason=fallback_reason,
    )
    primary = primary_checks(all_items, include_faq=include_faq)
    secondary = secondary_checks(all_items, include_faq=include_faq)
    primary_ok = sum(1 for i in primary if i.passed)

    with ui.expansion(
        "Revisão antes de publicar",
        icon="fact_check",
    ).classes("geo-checklist-panel w-full mt-4").props("default-opened"):
        ui.label(
            "Validação automática (H1, FAQ, tamanho e estrutura). "
            "Corrija itens em falha antes de publicar ou guardar no histórico."
        ).classes("geo-checklist__intro")

        with ui.element("div").classes("geo-checklist__section"):
            with ui.row().classes("items-center justify-between w-full mb-2"):
                ui.label("Essencial").classes("geo-checklist__section-title")
                ui.label(f"{primary_ok}/{len(primary)} OK").classes(
                    "geo-checklist__badge"
                    + (" geo-checklist__badge--ok" if primary_ok == len(primary) else "")
                )
            for item in primary:
                _render_validation_row(item)

        if not all(i.passed for i in primary):
            ui.label(
                "Regenere com IA, edite o Markdown ou ajuste o formulário."
            ).classes("geo-checklist__callout")

        if secondary:
            ui.separator().classes("my-3")
            sec_ok = sum(1 for i in secondary if i.passed)
            with ui.expansion(
                f"SEO e qualidade ({sec_ok}/{len(secondary)} OK)",
                icon="tune",
            ).classes("w-full").props("dense"):
                for item in secondary:
                    _render_validation_row(item)
