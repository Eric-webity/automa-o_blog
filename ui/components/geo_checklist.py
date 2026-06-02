"""Checklist de revisão GEO na aba Criar matéria (H1, FAQ, tamanho + revisão humana)."""

from __future__ import annotations

import re
from dataclasses import dataclass

from nicegui import ui

from services.blog import BlogBrief, BlogPostPackage
from services.blog_pipeline import BlogResult
from services.word_count import WORD_COUNT_WARNING_RATIO

_CERT_IN_H1 = re.compile(
    r"\b(ISO\s*\d+|OMS|ANVISA|FDA|CE\b|certificad[oa])\b",
    re.I,
)

# Itens principais pedidos na revisão editorial
_PRIMARY_IDS: tuple[str, ...] = ("h1_editorial", "faq", "word_count", "originality")


@dataclass
class ChecklistItem:
    """Item automático da checklist."""

    item_id: str
    label: str
    passed: bool
    hint: str = ""
    detail: str = ""


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
) -> list[ChecklistItem]:
    """Calcula verificações automáticas."""
    md = package.markdown or ""
    items: list[ChecklistItem] = []

    target = package.word_count_target or brief.word_count
    actual = package.word_count_actual or 0
    ratio = (actual / target) if target else 0
    ratio_ok = bool(target and actual and ratio >= WORD_COUNT_WARNING_RATIO)
    items.append(
        ChecklistItem(
            item_id="word_count",
            label="Tamanho do texto",
            passed=ratio_ok,
            hint="Abaixo de 85% da meta — expanda secções ou regenere com IA.",
            detail=f"{actual:,} / {target:,} palavras ({int(ratio * 100) if target else 0}% da meta)",
        )
    )

    has_faq_section = bool(
        re.search(r"^##\s+.*perguntas?\s+frequentes", md, re.I | re.M)
        or package.faq_items
    )
    if brief.include_faq:
        faq_count = len(package.faq_items) if package.faq_items else 0
        items.append(
            ChecklistItem(
                item_id="faq",
                label="Secção FAQ",
                passed=has_faq_section,
                hint="Inclua «## Perguntas frequentes» com 5–8 perguntas e respostas.",
                detail=f"{faq_count} itens no metadado" if faq_count else "Não detetada no Markdown",
            )
        )

    h1_match = re.search(r"^#\s+(.+)$", md, re.M)
    h1_text = h1_match.group(1).strip() if h1_match else ""
    h1_ok = bool(h1_text) and not _CERT_IN_H1.search(h1_text)
    items.append(
        ChecklistItem(
            item_id="h1_editorial",
            label="H1 editorial",
            passed=h1_ok,
            hint="Título sem siglas (ISO, OMS…) — use blocos de confiança em H3.",
            detail=h1_text[:80] + ("…" if len(h1_text) > 80 else "") if h1_text else "H1 em falta",
        )
    )

    desc = package.meta_description or ""
    items.append(
        ChecklistItem(
            item_id="meta_description",
            label="Meta description (50–160 caracteres)",
            passed=50 <= len(desc) <= 160,
            detail=f"{len(desc)} caracteres",
        )
    )

    items.append(
        ChecklistItem(
            item_id="h2_structure",
            label="Secções H2",
            passed=bool(re.search(r"^##\s+", md, re.M)),
            detail="Estrutura citável por IAs",
        )
    )

    sim_detail = ""
    if result.similarity_ratio is not None:
        sim_detail = f"~{int(result.similarity_ratio * 100)}% de similaridade com fonte"
    items.append(
        ChecklistItem(
            item_id="originality",
            label="Originalidade vs. fontes",
            passed=not result.similarity_warning,
            hint=result.similarity_warning or "Nenhuma proximidade excessiva detectada.",
            detail=sim_detail or "Sem URLs de referência ou texto distinto das fontes",
        )
    )

    if result.fallback_reason:
        items.append(
            ChecklistItem(
                item_id="llm_mode",
                label="Geração com IA",
                passed=False,
                hint=result.fallback_reason,
            )
        )

    return items


def _primary_items(items: list[ChecklistItem], brief: BlogBrief) -> list[ChecklistItem]:
    out: list[ChecklistItem] = []
    for item_id in _PRIMARY_IDS:
        if item_id == "faq" and not brief.include_faq:
            continue
        for item in items:
            if item.item_id == item_id:
                out.append(item)
                break
    return out


def _secondary_items(items: list[ChecklistItem], brief: BlogBrief) -> list[ChecklistItem]:
    primary_ids = set(_PRIMARY_IDS)
    return [i for i in items if i.item_id not in primary_ids]


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


def _render_auto_row(item: ChecklistItem) -> None:
    icon = "check_circle" if item.passed else "error_outline"
    color = "positive" if item.passed else "warning"
    row_cls = "geo-checklist__row geo-checklist__row--ok" if item.passed else "geo-checklist__row geo-checklist__row--pending"
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
    ).classes("geo-checklist-panel w-full mt-4").props("default-opened"):
        ui.label(
            "Use esta lista após cada geração. Os três pontos críticos (H1, FAQ e tamanho) "
            "são verificados automaticamente; confirme o resto manualmente antes de publicar."
        ).classes("geo-checklist__intro")

        # —— Essencial: H1, FAQ, tamanho ——
        with ui.element("div").classes("geo-checklist__section"):
            with ui.row().classes("items-center justify-between w-full mb-2"):
                ui.label("Essencial (automático)").classes("geo-checklist__section-title")
                ui.label(f"{primary_ok}/{len(primary)} OK").classes(
                    "geo-checklist__badge"
                    + (" geo-checklist__badge--ok" if primary_ok == len(primary) else "")
                )

            for item in primary:
                _render_auto_row(item)

        if not all(i.passed for i in primary):
            ui.label(
                "Corrija os itens em falta (regenerar, editar Markdown ou ajustar o formulário) "
                "antes de publicar."
            ).classes("geo-checklist__callout")

        # —— SEO / qualidade extra ——
        if secondary:
            ui.separator().classes("my-3")
            sec_ok = sum(1 for i in secondary if i.passed)
            with ui.expansion(
                f"SEO e qualidade ({sec_ok}/{len(secondary)} OK)",
                icon="tune",
            ).classes("w-full").props("dense"):
                for item in secondary:
                    _render_auto_row(item)

        # —— Revisão humana ——
        ui.separator().classes("my-4")
        with ui.element("div").classes("geo-checklist__section"):
            with ui.row().classes("items-center justify-between w-full mb-2"):
                ui.label("Revisão humana guiada").classes("geo-checklist__section-title")
                progress_label = ui.label(
                    f"{manual_ok}/{len(manual_steps)} confirmados"
                ).classes("geo-checklist__badge")

            ui.linear_progress(
                value=manual_ok / len(manual_steps) if manual_steps else 0,
                show_value=False,
            ).props(
                'color="primary" rounded size="8px"'
            ).classes("w-full mb-3")

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

                    cb = ui.checkbox(step.label, value=manual_done.get(step.item_id, False))
                    cb.classes("geo-checklist__manual-cb")
                    cb.on("update:model-value", _on_manual)
                    ui.label(step.guide).classes("geo-checklist__guide")

            _sync_progress()

            if state.get("complete"):
                ui.label("Revisão concluída — pode guardar no blog ou exportar.").classes(
                    "geo-checklist__success"
                )
