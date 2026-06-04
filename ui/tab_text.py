"""Aba: processar texto manual (layout Content Studio)."""

from __future__ import annotations

import asyncio
import json
import logging

from nicegui import run, ui

from core.insight_extractor import extract_insights_from_text, merge_insights
from db.models import ArticleStatus
from services.blog_publisher import save_post_to_blog
from services.background_jobs import (
    JobKind,
    get_background_job_service,
    run_text_job,
    should_queue_text,
)
from services.similarity_check import analyze_pasted_text_similarity
from services.url_pipeline import run_url_pipeline
from ui.components.article_review_panel import render_article_review_panel
from ui.components.similarity_banner import (
    SimilarityAlert,
    notify_similarity_if_needed,
    render_similarity_banner,
)
from ui.components.article_split_view import ArticleSplitView
from ui.components.background_job_panel import mount_background_job_tracker
from ui.components.faq_jsonld_export import render_faq_jsonld_export
from ui.components.geo_niche_panel import render_geo_niche_panel
from ui.constants import (
    ALERT_ERROR,
    ALERT_SUCCESS,
    ALERT_WARNING,
    geo_niche_select_options,
)
from ui.auth import require_session_user_id
from ui.session_scope import (
    account_scope_caption,
    reset_owned_tab_state,
    sync_config_session,
)
from ui.widgets import page_header

logger = logging.getLogger(__name__)

_FEATURE_TIPS = (
    "Identificação de cidades, estados e países.",
    "Extração de palavras-chave e categorias.",
    "Geração de resumo e artigo estruturado com IA.",
)


def build_tab_text(config) -> None:
    alert_box = ui.column().classes("w-full geo-text-results")
    result_box = ui.column().classes("w-full geo-text-results")
    save_state: dict = {"article_id": None, "owner_id": None}
    process_btn: ui.button | None = None

    with ui.element("div").classes("geo-text-page w-full"):
        page_header(
            "Extrator de texto manual",
            (
                "Cole o conteúdo da matéria para extrair entidades e estruturar o texto. "
                + account_scope_caption()
            ),
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

                    audience = (
                        ui.input(
                            placeholder="Ex: gestores de marketing, pacientes, investidores…",
                            value="Leitores interessados no tema",
                        )
                        .classes("w-full geo-text-glass-input mb-4")
                        .props("outlined dense")
                    )

                    niche_select = render_geo_niche_panel(
                        topic_input=title,
                        audience_input=audience,
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
                with ui.element("section").classes(
                    "geo-text-panel p-0 overflow-hidden w-full"
                ):
                    with ui.element("div").classes("geo-text-feature-hero"):
                        ui.element("div").classes("geo-text-feature-hero__overlay")
                        ui.html(
                            '<span class="geo-text-feature-badge">IA Powered</span>'
                        )
                    with ui.element("div").classes("geo-text-feature-body"):
                        ui.label("Como funciona?").classes(
                            "geo-section-title text-primary"
                        )
                        with ui.element("ul").classes("geo-text-feature-list"):
                            for tip in _FEATURE_TIPS:
                                with ui.element("li").classes("geo-text-feature-item"):
                                    ui.icon("check_circle", size="sm").classes(
                                        "text-secondary mt-0.5"
                                    )
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
        owner_id = require_session_user_id()
        try:
            try:
                save_result = await save_post_to_blog(
                    title=title,
                    markdown_content=result.article.markdown or "",
                    json_index=result.ai_index or None,
                    article_id=save_state["article_id"],
                    status=ArticleStatus.DRAFT.value,
                    user_id=owner_id,
                )
            except ValueError:
                save_result = await save_post_to_blog(
                    title=title,
                    markdown_content=result.article.markdown or "",
                    json_index=result.ai_index or None,
                    status=ArticleStatus.DRAFT.value,
                    user_id=owner_id,
                )
            save_state["article_id"] = save_result.article_id
            with result_box:
                ui.label(f"Salva no histórico (#{save_result.article_id}).").classes(
                    ALERT_SUCCESS
                )
        except Exception as exc:
            with alert_box:
                ui.label(f"Não foi possível salvar no histórico: {exc}").classes(
                    ALERT_WARNING
                )

    def _render_text_success(result, ins, *, source_text: str = "") -> None:
        pasted_sim = (
            analyze_pasted_text_similarity(result.article.markdown, source_text)
            if source_text.strip()
            else None
        )
        sim_alert = SimilarityAlert.from_report(
            pasted_sim
        ) or SimilarityAlert.from_url_result(result)

        result_box.clear()
        with alert_box:
            render_similarity_banner(sim_alert)
            if result.fallback_reason:
                ui.label(result.fallback_reason).classes(ALERT_WARNING)
        notify_similarity_if_needed(sim_alert)

        with result_box:
            ui.label("Texto processado com sucesso.").classes(ALERT_SUCCESS)

            with ui.tabs().classes("w-full geo-inner-tabs mt-2") as tabs:
                t_ins = ui.tab("Insights")
                t_idx = ui.tab("Índice IA")
                t_skel = ui.tab("Esqueleto")
                t_art = ui.tab("Artigo")
                t_faq_ld = ui.tab("FAQ JSON-LD")

            with ui.tab_panels(tabs, value=t_art).classes("w-full"):
                with ui.tab_panel(t_ins):
                    m = result.merged
                    ui.label(f"Tema: {m.get('tema_central', '')}").classes(
                        "geo-page-desc"
                    )
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
                        ui.label(f"Salvo: {result.index_path}").classes(
                            "geo-meta-caption"
                        )
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
                    render_article_review_panel(
                        art.markdown,
                        include_faq=True,
                        fallback_reason=result.fallback_reason,
                        similarity_warning=(
                            sim_alert.warning
                            if sim_alert
                            else result.similarity_warning
                        ),
                        show_word_banner=False,
                    )
                with ui.tab_panel(t_faq_ld):
                    render_faq_jsonld_export(
                        faq_items=None,
                        markdown=result.article.markdown,
                        page_title=title.value or "Matéria manual",
                    )

    def _touch_save_session() -> None:
        sync_config_session(config)
        reset_owned_tab_state(save_state, user_id=require_session_user_id())

    _touch_save_session()

    async def process() -> None:
        _touch_save_session()
        alert_box.clear()
        result_box.clear()

        body_text = (body.value or "").strip()
        if not body_text:
            with alert_box:
                ui.label("Cole o texto da matéria.").classes(ALERT_WARNING)
            return

        title_val = title.value or "Matéria manual"
        niche_options = geo_niche_select_options()
        geo_niche = niche_options.get(niche_select.value, "generic")

        def _enable_process_btn() -> None:
            if process_btn:
                process_btn.enable()

        def _on_text_failed(err: str) -> None:
            result_box.clear()
            with alert_box:
                ui.label(f"Erro: {err}").classes(ALERT_ERROR)
            _enable_process_btn()

        async def _finish_text(payload: dict) -> None:
            try:
                _render_text_success(
                    payload["result"],
                    payload["insight"],
                    source_text=payload.get("source_text", ""),
                )
                await _persist_to_history(payload["result"])
            except Exception as exc:
                logger.exception("Falha ao apresentar resultado do texto: %s", exc)
                _on_text_failed(str(exc))
            finally:
                _enable_process_btn()

        if should_queue_text(body_text):
            if process_btn:
                process_btn.disable()
            with result_box:
                tracker_host = ui.column().classes("w-full")
            job_id = get_background_job_service().submit(
                lambda report: run_text_job(
                    report,
                    body=body_text,
                    title=title_val,
                    config=config,
                    geo_niche=geo_niche,
                ),
                label=f"Texto: {title_val[:40]}",
                kind=JobKind.TEXT,
            )

            def _on_text_done(payload) -> None:
                if isinstance(payload, dict) and "source_text" not in payload:
                    payload = {**payload, "source_text": body_text}
                asyncio.create_task(_finish_text(payload))

            mount_background_job_tracker(
                job_id,
                host=tracker_host,
                on_completed=_on_text_done,
                on_failed=_on_text_failed,
            )
            return

        if process_btn:
            process_btn.disable()

        with result_box:
            with ui.row().classes("items-center gap-3 geo-text-panel py-4 px-6"):
                ui.spinner(size="md").classes("geo-loading-spinner")
                with ui.column().classes("gap-0"):
                    ui.label("A processar o seu texto…").classes(
                        "text-body2 font-medium"
                    )
                    ui.label("Isto pode levar alguns segundos.").classes(
                        "text-caption text-grey-7"
                    )

        try:
            ins = await run.io_bound(
                extract_insights_from_text,
                body_text,
                title=title_val,
                use_advanced=config.use_advanced,
            )
            if not ins:
                result_box.clear()
                with alert_box:
                    ui.label("Não foi possível extrair insights.").classes(ALERT_ERROR)
                return

            merged = merge_insights([ins])
            merged["geo_niche"] = geo_niche

            result = await run.io_bound(
                run_url_pipeline,
                [ins],
                merged,
                use_llm=config.use_llm,
                provider=config.provider,
                manager=config.ai_manager,
                geo_niche=geo_niche,
            )
            _render_text_success(result, ins, source_text=body_text)
            await _persist_to_history(result)
        except Exception as exc:
            logger.exception("Erro ao processar texto: %s", exc)
            ui.notify(f"Erro: {exc}", type="negative")
            _on_text_failed(str(exc))
        finally:
            _enable_process_btn()

    if process_btn:
        process_btn.on("click", lambda: asyncio.create_task(process()))
