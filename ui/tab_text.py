"""Aba: processar texto manual (layout Content Studio)."""

from __future__ import annotations

import json

from nicegui import run, ui

from core.insight_extractor import extract_insights_from_text, merge_insights
from db.models import ArticleStatus
from services.blog_publisher import save_post_to_blog
from services.url_pipeline import run_url_pipeline
from ui.components.article_split_view import ArticleSplitView
from ui.constants import ALERT_ERROR, ALERT_SUCCESS, ALERT_WARNING
from ui.widgets import page_header

_FEATURE_TIPS = (
    "Identificação de cidades, estados e países.",
    "Extração de palavras-chave e categorias.",
    "Geração de resumo e artigo estruturado com IA.",
)


def build_tab_text(config) -> None:
    alert_box = ui.column().classes("w-full geo-text-results")
    result_box = ui.column().classes("w-full geo-text-results")
    save_state: dict = {"article_id": None}
    process_btn: ui.button | None = None

    with ui.element("div").classes("geo-text-page w-full"):
        page_header(
            "Extrator de texto manual",
            "Cole o conteúdo da sua matéria abaixo. A IA processará o texto "
            "para identificar entidades geográficas, metadados e estruturar o conteúdo.",
            eyebrow="Texto",
        )

        with ui.element("div").classes("geo-text-grid w-full"):
            with ui.element("div").classes("geo-text-main"):
                with ui.element("section").classes("geo-text-panel w-full"):
                    ui.label("Título").classes("geo-text-field-label")
                    title = (
                        ui.input(
                            placeholder="Digite o título da matéria ou do projeto",
                            value="Matéria manual",
                        )
                        .classes("w-full geo-text-glass-input mb-4")
                        .props("outlined dense")
                    )

                    ui.label("Texto da matéria").classes("geo-text-field-label")
                    body = (
                        ui.textarea(
                            placeholder=(
                                "Cole aqui o texto completo da sua notícia ou artigo..."
                            ),
                        )
                        .classes("w-full geo-text-glass-input")
                        .props("outlined rows=12")
                    )

                    with ui.element("div").classes("geo-text-process-row"):
                        process_btn = (
                            ui.button("Processar texto", icon="description")
                            .props("no-caps unelevated")
                            .classes("geo-text-process-btn")
                        )

            with ui.element("aside").classes("geo-text-side"):
                with ui.element("section").classes("geo-text-panel p-0 overflow-hidden w-full"):
                    with ui.element("div").classes("geo-text-feature-hero"):
                        ui.element("div").classes("geo-text-feature-hero__overlay")
                        ui.html('<span class="geo-text-feature-badge">IA Powered</span>')
                    with ui.element("div").classes("geo-text-feature-body"):
                        ui.label("Como funciona?").classes("geo-section-title text-primary")
                        with ui.element("ul").classes("geo-text-feature-list"):
                            for tip in _FEATURE_TIPS:
                                with ui.element("li").classes("geo-text-feature-item"):
                                    ui.icon("check_circle", size="sm").classes("text-secondary mt-0.5")
                                    ui.html(f"<p>{tip}</p>")

                with ui.element("section").classes("geo-text-panel w-full"):
                    ui.label("Configurações Rápidas").classes("geo-text-quick-title")

                    def on_advanced(e) -> None:
                        config.use_advanced = bool(e.value)

                    def on_llm(e) -> None:
                        config.use_llm = bool(e.value)

                    adv_cls = (
                        "geo-text-quick-row geo-text-quick-row--active"
                        if config.use_advanced
                        else "geo-text-quick-row"
                    )
                    with ui.element("div").classes(adv_cls):
                        ui.label("Extração geográfica").classes("!text-inherit")
                        adv_switch = ui.switch(value=config.use_advanced).props(
                            "dense color=primary"
                        )
                        adv_switch.on("update:model-value", on_advanced)

                    llm_cls = (
                        "geo-text-quick-row geo-text-quick-row--active"
                        if config.use_llm
                        else "geo-text-quick-row"
                    )
                    with ui.element("div").classes(llm_cls):
                        ui.label("Gerar artigo com IA").classes("!text-inherit")
                        llm_switch = ui.switch(value=config.use_llm).props(
                            "dense color=primary"
                        )
                        llm_switch.on("update:model-value", on_llm)

                    with ui.element("div").classes("geo-text-quick-row"):
                        ui.label("Provedor").classes("!text-inherit")
                        ready = config.ready_providers or []
                        provider_label = ", ".join(ready) if ready else "auto"
                        ui.label(provider_label).classes("text-caption text-primary")

        alert_box
        result_box

    async def _persist_to_history(result) -> None:
        """Salva/atualiza a matéria gerada no histórico (banco), reutilizando o id."""
        title = (
            result.merged.get("tema_central")
            or result.merged.get("entidade_intencao")
            or "Matéria gerada a partir de texto"
        )
        try:
            try:
                save_result = await save_post_to_blog(
                    title=title,
                    markdown_content=result.article.markdown or "",
                    json_index=result.ai_index or None,
                    article_id=save_state["article_id"],
                    status=ArticleStatus.DRAFT.value,
                )
            except ValueError:
                save_result = await save_post_to_blog(
                    title=title,
                    markdown_content=result.article.markdown or "",
                    json_index=result.ai_index or None,
                    status=ArticleStatus.DRAFT.value,
                )
            save_state["article_id"] = save_result.article_id
            with result_box:
                ui.label(
                    f"Salva no histórico (#{save_result.article_id})."
                ).classes(ALERT_SUCCESS)
        except Exception as exc:
            with alert_box:
                ui.label(
                    f"Não foi possível salvar no histórico: {exc}"
                ).classes(ALERT_WARNING)

    async def process() -> None:
        alert_box.clear()
        result_box.clear()

        if not body.value or not body.value.strip():
            with alert_box:
                ui.label("Cole o texto da matéria.").classes(ALERT_WARNING)
            return

        if process_btn:
            process_btn.disable()

        with result_box:
            with ui.row().classes("items-center gap-3 geo-text-panel py-4 px-6"):
                ui.spinner(size="md").classes("geo-loading-spinner")
                with ui.column().classes("gap-0"):
                    ui.label("A processar o seu texto…").classes("text-body2 font-medium")
                    ui.label("Isto pode levar alguns segundos.").classes("text-caption text-grey-7")

        try:
            ins = await run.io_bound(
                extract_insights_from_text,
                body.value,
                title=title.value or "Matéria manual",
                use_advanced=config.use_advanced,
            )
            if not ins:
                result_box.clear()
                with alert_box:
                    ui.label("Não foi possível extrair insights.").classes(
                        ALERT_ERROR
                    )
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
                    ui.label(result.fallback_reason).classes(ALERT_WARNING)

            with result_box:
                ui.label("Texto processado com sucesso.").classes(ALERT_SUCCESS)

                with ui.tabs().classes("w-full geo-inner-tabs mt-2") as tabs:
                    t_ins = ui.tab("Insights")
                    t_idx = ui.tab("Índice IA")
                    t_skel = ui.tab("Esqueleto")
                    t_art = ui.tab("Artigo")

                with ui.tab_panels(tabs, value=t_art).classes("w-full"):
                    with ui.tab_panel(t_ins):
                        m = result.merged
                        ui.label(f"Tema: {m.get('tema_central', '')}").classes("geo-page-desc")
                        ui.label(f"Entidade: {m.get('entidade_intencao', '')}").classes(
                            "geo-meta-caption mb-2"
                        )
                        ui.label("Keywords: " + ", ".join(ins.keywords[:16])).classes(
                            "text-body2"
                        )
                        ui.label("Resumo: " + ins.summary[:800]).classes("text-body2 mt-2")
                    with ui.tab_panel(t_idx):
                        ui.code(
                            json.dumps(result.ai_index, indent=2, ensure_ascii=False),
                            language="json",
                        ).classes("w-full")
                        if result.index_path:
                            ui.label(f"Salvo: {result.index_path}").classes("geo-meta-caption")
                    with ui.tab_panel(t_skel):
                        ui.markdown(result.skeleton.markdown).classes("w-full")
                    with ui.tab_panel(t_art):
                        art = result.article
                        ui.label(
                            f"Modo: {art.provider_used or ('IA' if art.used_llm else 'local')}"
                        ).classes("geo-meta-caption mb-2")
                        ArticleSplitView(
                            art.markdown,
                            footer=f"Salvo: {result.article_path}",
                            live_preview=True,
                        )

            await _persist_to_history(result)
        finally:
            if process_btn:
                process_btn.enable()

    if process_btn:
        process_btn.on("click", process)
