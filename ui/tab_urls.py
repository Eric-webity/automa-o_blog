"""Aba: processar URLs."""

from __future__ import annotations

import json

from nicegui import run, ui

from core.insight_extractor import extract_insights, merge_insights
from services.article_fetcher import fetch_many
from services.url_pipeline import run_url_pipeline
from ui.components.article_split_view import ArticleSplitView
from ui.widgets import geo_textarea, loading_status, page_header, primary_button


def build_tab_urls(config) -> None:
    page_header(
        "Processar URLs de matérias",
        "Cole links de referência para extrair insights, gerar índice IA e artigo GEO.",
    )

    urls_input = geo_textarea(
        "URLs (uma por linha)",
        placeholder="https://...\nhttps://...",
        rows=6,
    )

    alert_box = ui.column().classes("w-full")
    result_box = ui.column().classes("w-full mt-2")

    async def process() -> None:
        alert_box.clear()
        result_box.clear()
        urls = [u.strip() for u in (urls_input.value or "").splitlines() if u.strip()]
        if not urls:
            with alert_box:
                ui.label("Informe pelo menos uma URL.").classes("geo-alert geo-alert--warning")
            return

        with result_box:
            loading_status("A buscar matérias…")

        fetched = await run.io_bound(fetch_many, urls)
        warnings = [f"{a.url}: {a.error}" for a in fetched if a.error]

        insights_list = await run.io_bound(
            lambda: [
                ins
                for a in fetched
                if (ins := extract_insights(a, use_advanced=config.use_advanced))
            ]
        )

        if not insights_list:
            result_box.clear()
            with alert_box:
                ui.label("Nenhuma matéria processada.").classes("geo-alert geo-alert--error")
                for w in warnings:
                    ui.label(w).classes("geo-meta-caption")
            return

        merged = merge_insights(insights_list)
        result = await run.io_bound(
            run_url_pipeline,
            insights_list,
            merged,
            use_llm=config.use_llm,
            provider=config.provider,
            manager=config.ai_manager,
        )

        result_box.clear()
        with alert_box:
            for w in warnings:
                ui.label(w).classes("geo-meta-caption")
            if result.fallback_reason:
                ui.label(result.fallback_reason).classes("geo-alert geo-alert--warning")

        with result_box:
            ui.label(f"{len(insights_list)} matéria(s) processada(s).").classes(
                "geo-alert geo-alert--success"
            )
            with ui.tabs().classes("w-full geo-inner-tabs") as tabs:
                t1 = ui.tab("Insights")
                t2 = ui.tab("Índice IA")
                t3 = ui.tab("Esqueleto")
                t4 = ui.tab("Artigo")

            with ui.tab_panels(tabs, value=t1).classes("w-full"):
                with ui.tab_panel(t1):
                    m = result.merged
                    ui.label(f"Tema: {m.get('tema_central', '')}").classes("geo-page-desc")
                    ui.label(f"Entidade: {m.get('entidade_intencao', '')}").classes(
                        "geo-meta-caption mb-4"
                    )
                    for ins in result.insights:
                        with ui.expansion(f"{ins.title} · {ins.extraction_mode}"):
                            ui.label("Keywords: " + ", ".join(ins.keywords[:12]))
                            ui.label("Resumo: " + ins.summary[:500])
                with ui.tab_panel(t2):
                    ui.code(
                        json.dumps(result.ai_index, indent=2, ensure_ascii=False),
                        language="json",
                    ).classes("w-full")
                    ui.label(f"Salvo: {result.index_path}").classes("geo-meta-caption")
                with ui.tab_panel(t3):
                    ui.markdown(result.skeleton.markdown).classes("w-full")
                with ui.tab_panel(t4):
                    art = result.article
                    ui.label(
                        f"Modo: {art.provider_used or ('IA' if art.used_llm else 'local')}"
                    ).classes("geo-meta-caption mb-2")
                    ArticleSplitView(
                        art.markdown,
                        footer=f"Salvo: {result.article_path}",
                        live_preview=True,
                    )

    primary_button("Processar URLs", process, icon="play_arrow")
