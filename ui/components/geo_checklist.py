"""Checklist de revisão GEO na aba Criar matéria (H1, FAQ, tamanho + revisão humana)."""

from __future__ import annotations

from dataclasses import dataclass

from nicegui import ui

from services.article_validation import (
    ValidationItem,
    primary_checks,
    secondary_checks,
    validate_article_markdown,
)
from services.blog import BlogBrief, BlogPostPackage
from services.blog_pipeline import BlogResult

# Reexport para testes e compatibilidade
ChecklistItem = ValidationItem


@dataclass
class ManualCheckItem:
    """Passo de confirmação manual pelo revisor."""

    item_id: str
    label: str
    guide: str


def evaluate_geo_checklist(
    brief: BlogBrief,
    package: BlogPostPackage,
    result: BlogResult,
) -> list[ValidationItem]:
    """Calcula verificações automáticas."""
    return validate_article_markdown(
        package.markdown or "",
        target_words=package.word_count_target or brief.word_count,
        include_faq=brief.include_faq,
        meta_description=package.meta_description or "",
        faq_items=package.faq_items,
        similarity_warning=result.similarity_warning,
        fallback_reason=result.fallback_reason,
    )


def _primary_items(
    items: list[ValidationItem], brief: BlogBrief
) -> list[ValidationItem]:
    return primary_checks(items, include_faq=brief.include_faq)


def _secondary_items(
    items: list[ValidationItem], brief: BlogBrief
) -> list[ValidationItem]:
    return secondary_checks(items, include_faq=brief.include_faq)


def _manual_steps(brief: BlogBrief, result: BlogResult) -> list[ManualCheckItem]:
    steps: list[ManualCheckItem] = [
        ManualCheckItem(
            item_id="review_read",
            label="Li o artigo completo no preview",
            guide="Percorra introdução, desenvolvimento e conclusão antes de marcar os itens abaixo.",
        ),
    ]
    if result.similarity_warning:
        steps.append(
            ManualCheckItem(
                item_id="review_originality",
                label="Reescrevi trechos parecidos com as fontes",
                guide=(
                    "Parafraseie ou cite com link; evite copiar frases longas das URLs de referência."
                ),
            )
        )
    steps.extend(
        [
            ManualCheckItem(
                item_id="review_h1",
                label="H1 transmite o tema sem jargão de certificação",
                guide="O título deve convidar à leitura; selos e normas ficam em secções H3.",
            ),
            ManualCheckItem(
                item_id="review_size",
                label="Profundidade adequada ao objetivo",
                guide="Confirme se cada H2 responde ao que o leitor espera; expanda o que estiver superficial.",
            ),
        ]
    )
    if brief.include_faq:
        steps.append(
            ManualCheckItem(
                item_id="review_faq",
                label="FAQ útil para motores generativos",
                guide="Respostas diretas, 2–4 frases; evite copiar texto das fontes.",
            )
        )
    steps.extend(
        [
            ManualCheckItem(
                item_id="review_facts",
                label="Dados e afirmações conferidos",
                guide="Números, estudos e comparações batem com as URLs de referência.",
            ),
            ManualCheckItem(
                item_id="review_publish",
                label="Pronto para guardar ou publicar",
                guide="Só marque quando tiver aplicado correções no editor, se necessário.",
            ),
        ]
    )
    return steps


def _render_auto_row(item: ValidationItem) -> None:
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


def render_geo_checklist(
    brief: BlogBrief,
    package: BlogPostPackage,
    result: BlogResult,
    *,
    checklist_state: dict | None = None,
) -> None:
    """Checklist GEO: H1, FAQ, tamanho (auto) + revisão humana guiada."""
    state = checklist_state if checklist_state is not None else {}
    manual_done: dict[str, bool] = state.setdefault("manual", {})

    all_auto = evaluate_geo_checklist(brief, package, result)
    primary = _primary_items(all_auto, brief)
    secondary = _secondary_items(all_auto, brief)
    manual_steps = _manual_steps(brief, result)

    primary_ok = sum(1 for i in primary if i.passed)
    manual_ok = sum(1 for s in manual_steps if manual_done.get(s.item_id))

    with ui.expansion(
        "Revisão antes de publicar",
        icon="fact_check",
    ).classes(
        "geo-checklist-panel w-full mt-4"
    ).props("default-opened"):
        ui.label(
            "Use esta lista após cada geração. Os três pontos críticos (H1, FAQ e tamanho) "
            "são verificados automaticamente; confirme o resto manualmente antes de publicar."
        ).classes("geo-checklist__intro")

        with ui.element("div").classes("geo-checklist__section"):
            with ui.row().classes("items-center justify-between w-full mb-2"):
                ui.label("Essencial (automático)").classes(
                    "geo-checklist__section-title"
                )
                ui.label(f"{primary_ok}/{len(primary)} OK").classes(
                    "geo-checklist__badge"
                    + (
                        " geo-checklist__badge--ok"
                        if primary_ok == len(primary)
                        else ""
                    )
                )

            for item in primary:
                _render_auto_row(item)

        if not all(i.passed for i in primary):
            ui.label(
                "Corrija os itens em falta (regenerar, editar Markdown ou ajustar o formulário) "
                "antes de publicar."
            ).classes("geo-checklist__callout")

        if secondary:
            ui.separator().classes("my-3")
            sec_ok = sum(1 for i in secondary if i.passed)
            with ui.expansion(
                f"SEO e qualidade ({sec_ok}/{len(secondary)} OK)",
                icon="tune",
            ).classes("w-full").props("dense"):
                for item in secondary:
                    _render_auto_row(item)

        ui.separator().classes("my-4")
        with ui.element("div").classes("geo-checklist__section"):
            with ui.row().classes("items-center justify-between w-full mb-2"):
                ui.label("Revisão humana guiada").classes(
                    "geo-checklist__section-title"
                )
                progress_label = ui.label(
                    f"{manual_ok}/{len(manual_steps)} confirmados"
                ).classes("geo-checklist__badge")

            ui.linear_progress(
                value=manual_ok / len(manual_steps) if manual_steps else 0,
                show_value=False,
            ).props('color="primary" rounded size="8px"').classes("w-full mb-3")

            def _sync_progress() -> None:
                done = sum(1 for s in manual_steps if manual_done.get(s.item_id))
                progress_label.text = f"{done}/{len(manual_steps)} confirmados"
                state["complete"] = done == len(manual_steps) and all(
                    i.passed for i in primary
                )

            for step in manual_steps:
                with ui.element("div").classes("geo-checklist__manual-step"):

                    def _on_manual(e, sid=step.item_id) -> None:
                        manual_done[sid] = bool(e.value)
                        _sync_progress()

                    cb = ui.checkbox(
                        step.label, value=manual_done.get(step.item_id, False)
                    )
                    cb.classes("geo-checklist__manual-cb")
                    cb.on("update:model-value", _on_manual)
                    ui.label(step.guide).classes("geo-checklist__guide")

            _sync_progress()

            if state.get("complete"):
                ui.label(
                    "Revisão concluída — pode guardar no blog ou exportar."
                ).classes("geo-checklist__success")
