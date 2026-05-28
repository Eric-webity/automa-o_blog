"""Aba: texto manual."""

from __future__ import annotations

from nicegui import run, ui

from core.insight_extractor import extract_insights_from_text, merge_insights
from services.url_pipeline import run_url_pipeline
from ui.widgets import geo_input, geo_textarea, loading_status, page_header, primary_button


def build_tab_text(config) -> None:
    page_header("Processar texto manual", "Cole o conteúdo de uma matéria para extrair insights e gerar artigo.")
    title = geo_input("Título", value="Matéria manual")
    body = geo_textarea("Texto da matéria", rows=10)
    alert_box = ui.column().classes("w-full")
    result_box = ui.column().classes("w-full mt-4")

    async def process():
        alert_box.clear()
        result_box.clear()
        if not body.value or not body.value.strip():
            with alert_box:
                ui.label("Cole o texto.").classes("geo-alert geo-alert--warning")
            return

        with result_box:
            loading_status("A processar texto…")

        ins = await run.io_bound(
            extract_insights_from_text,
            body.value,
            title=title.value or "Matéria manual",
            use_advanced=config.use_advanced,
        )
        if not ins:
            result_box.clear()
            with alert_box:
                ui.label("Não foi possível extrair insights.").classes("geo-alert geo-alert--error")
            return

        merged = merge_insights([ins])
        result = await run.io_bound(
            run_url_pipeline,
            [ins],
            merged,
            use_llm=config.use_llm,
            provider=config.provider,
            manager=config.ai_manager,
        )

        result_box.clear()
        with alert_box:
            if result.fallback_reason:
                ui.label(result.fallback_reason).classes("geo-alert geo-alert--warning")

        with result_box:
            ui.label("Texto processado.").classes("geo-alert geo-alert--success")
            ui.markdown(result.article.markdown)

    primary_button("Processar texto", process, icon="description")
