"""Aba: criar matéria para blog (layout Content Studio)."""

from __future__ import annotations

import asyncio
import json
import logging

from nicegui import run, ui

from db.models import ArticleStatus
from services.article_validation import evaluate_brief_preflight, has_blocking_issues
from services.blog import BlogBrief, parse_keywords
from services.blog.brief import LONG_FORM_THRESHOLD
from services.background_jobs import (
    JobKind,
    get_background_job_service,
    run_blog_job,
    should_queue_blog,
)
from services.blog_pipeline import run_blog_pipeline, run_blog_pipeline_async
from services.article_history import build_history_json_index, index_from_blog_package
from services.blog_publisher import save_post_to_blog
from ui.components.background_job_panel import mount_background_job_tracker
from ui.components.agent_progress import AgentProgressPanel
from ui.components.article_split_view import normalize_preview_markdown
from ui.components.faq_jsonld_export import render_faq_jsonld_export
from ui.components.brief_preflight import render_brief_preflight
from ui.components.geo_checklist import render_geo_checklist
from ui.components.geo_niche_panel import render_geo_niche_panel
from ui.components.similarity_banner import (
    notify_similarity_if_needed,
    render_similarity_banner,
)
from ui.components.url_cache_notice import render_url_cache_banner
from ui.components.word_count_banner import (
    notify_word_count_if_needed,
    render_word_count_banner,
)
from ui.constants import (
    ALERT_ERROR,
    ALERT_SUCCESS,
    ALERT_WARNING,
    BLOG_TONE_OPTIONS,
    BLOG_WORD_COUNT_OPTIONS,
    blog_complexity_for_words,
    blog_tone_value,
    blog_word_count,
    geo_niche_select_options,
    provider_label,
    provider_select_options,
)
from ui.auth import require_session_user_id
from ui.session_scope import reset_owned_tab_state, sync_config_session
from ui.widgets import page_header

logger = logging.getLogger(__name__)


def build_tab_blog(config) -> None:
    alert_box: ui.column | None = None
    result_box: ui.column | None = None
    complexity_label: ui.label | None = None
    complexity_fill = None
    estimate_label: ui.label | None = None
    keywords_chips_box = None
    generate_btn: ui.button | None = None

    article_state: dict = {
        "id": None,
        "owner_id": None,
        "markdown": "",
        "editor": None,
        "preview": None,
        "meta": {},
        "provider": "",
        "checklist": {"manual": {}, "complete": False},
    }

    def _touch_article_session() -> int:
        sync_config_session(config)
        uid = require_session_user_id()
        reset_owned_tab_state(article_state, user_id=uid)
        return uid

    provider_options = provider_select_options(config.ready_providers or [])

    with ui.element("div").classes("geo-blog-page w-full"):
        page_header(
            "Criar nova matéria",
            "Defina os parâmetros do seu conteúdo e deixe a IA gerar um artigo "
            "otimizado para SEO e engajamento.",
            eyebrow="Editor",
        )

        with ui.element("div").classes("geo-blog-grid w-full"):
            with ui.element("div").classes("geo-blog-main"):
                with ui.element("section").classes(
                    "geo-blog-card geo-blog-card--accent-primary w-full"
                ):
                    with ui.element("h3").classes("geo-blog-card__title"):
                        ui.icon("text_fields").classes("text-primary")
                        ui.label("Contexto do conteúdo")

                    with ui.column().classes("w-full gap-4"):
                        ui.label("Tema principal").classes("geo-blog-field-label")
                        topic = (
                            ui.input(placeholder="Ex: melhor CRM para PMEs")
                            .classes("w-full geo-blog-input")
                            .props("outlined dense")
                        )

                        ui.label("Público-alvo").classes("geo-blog-field-label")
                        audience = (
                            ui.input(
                                placeholder="Ex: gestores de marketing, freelancers tech…",
                                value="Leitores interessados no tema",
                            )
                            .classes("w-full geo-blog-input")
                            .props("outlined dense")
                        )

                        niche_select = render_geo_niche_panel(
                            topic_input=topic,
                            audience_input=audience,
                        )

                        ui.label("Palavras-chave").classes("geo-blog-field-label")
                        keywords_chips_box = ui.element("div").classes(
                            "geo-blog-keyword-chips"
                        )
                        keywords = (
                            ui.input(
                                placeholder="Separe por vírgula — ex: SEO, content marketing",
                            )
                            .classes("w-full geo-blog-input")
                            .props("outlined dense")
                        )

                        ui.label("Ângulo editorial").classes("geo-blog-field-label")
                        angle = (
                            ui.textarea(
                                placeholder="Qual a abordagem principal deste texto?",
                            )
                            .classes("w-full geo-blog-input")
                            .props("outlined rows=3")
                        )

                with ui.element("section").classes(
                    "geo-blog-card geo-blog-card--accent-secondary w-full"
                ):
                    with ui.element("h3").classes("geo-blog-card__title"):
                        ui.icon("analytics").classes("text-secondary")
                        ui.label("Estrutura e links")

                    ui.label("Links de referência (um por linha)").classes(
                        "geo-blog-field-label"
                    )
                    refs = (
                        ui.textarea(
                            placeholder="Cole aqui os links que servirão de base…",
                        )
                        .classes("w-full geo-blog-input font-mono")
                        .props("outlined rows=4")
                    )

                    with ui.element("div").classes("geo-blog-faq-row mt-4"):
                        include_faq = ui.switch(value=True).props("dense color=primary")
                        with ui.column().classes("gap-0"):
                            ui.label("Incluir secção de FAQ").classes(
                                "geo-blog-faq-row__title"
                            )
                            ui.label(
                                "Gera automaticamente perguntas frequentes baseadas no conteúdo."
                            ).classes("geo-blog-faq-row__desc")

            with ui.element("aside").classes("geo-blog-side"):
                with ui.element("section").classes(
                    "geo-blog-card geo-blog-tone-card w-full"
                ):
                    ui.label("Configurações de tom").classes("geo-blog-tone-title")

                    tone = ui.select(
                        list(BLOG_TONE_OPTIONS.keys()),
                        label="Tom de voz",
                        value="Informativo",
                    ).classes("w-full geo-blog-input mb-3")

                    word_count = ui.select(
                        list(BLOG_WORD_COUNT_OPTIONS.keys()),
                        label="Extensão estimada",
                        value="Longo (~2 500 palavras)",
                    ).classes("w-full geo-blog-input mb-3")

                    long_hint = ui.label("").classes("text-caption text-grey-7 mb-2")

                    brand = (
                        ui.input(
                            "Marca / site",
                            placeholder="Opcional",
                        )
                        .classes("w-full geo-blog-input mb-3")
                        .props("outlined dense")
                    )

                    cta = (
                        ui.input(
                            "Chamada para ação (CTA)",
                            placeholder="Ex: Agende uma demo gratuita",
                        )
                        .classes("w-full geo-blog-input mb-3")
                        .props("outlined dense")
                    )

                    provider_select = (
                        ui.select(
                            provider_options,
                            label="Provedor de IA",
                            value="auto",
                        )
                        .classes("w-full geo-blog-input")
                        .props("outlined dense")
                    )

                with ui.element("section").classes("geo-blog-card w-full"):
                    with ui.element("div").classes("geo-blog-status-hero"):
                        with ui.element("div").classes("geo-blog-status-hero__overlay"):
                            ui.label("Visual do blog").classes(
                                "geo-blog-status-hero__title"
                            )
                            ui.label("Otimizado para layout mobile-first").classes(
                                "geo-blog-status-hero__subtitle"
                            )

                    with ui.element("div").classes("geo-blog-complexity-row"):
                        ui.label("Complexidade")
                        complexity_label = ui.label("")

                    with ui.element("div").classes("geo-blog-complexity-bar"):
                        complexity_fill = ui.element("div").classes(
                            "geo-blog-complexity-fill"
                        )

                    estimate_label = ui.label("").classes("geo-blog-estimate")

                    preflight_host = ui.element("div").classes("w-full mb-2")

                    generate_btn = (
                        ui.button("Gerar matéria para blog", icon="auto_awesome")
                        .props("no-caps unelevated")
                        .classes("geo-blog-generate-btn w-full")
                    )

        alert_box = ui.column().classes("w-full geo-blog-results")
        result_box = ui.column().classes("w-full geo-blog-results")

    def render_keyword_chips() -> None:
        keywords_chips_box.clear()
        items = parse_keywords(keywords.value or "")
        if not items:
            return
        with keywords_chips_box:
            for kw in items[:8]:

                def remove_kw(_e, word=kw) -> None:
                    current = parse_keywords(keywords.value or "")
                    current = [k for k in current if k.lower() != word.lower()]
                    keywords.value = ", ".join(current)
                    render_keyword_chips()

                with ui.element("span").classes("geo-blog-chip"):
                    ui.label(kw)
                    ui.button(icon="close", on_click=remove_kw).props(
                        "flat round dense size=xs"
                    ).classes("min-w-0 !p-0")

    def update_complexity() -> None:
        wc = blog_word_count(word_count.value)
        label, pct, eta = blog_complexity_for_words(wc)
        complexity_label.text = label
        complexity_fill.style(f"width: {pct}%")
        estimate_label.text = f"Tempo estimado de geração: {eta}"
        if wc >= LONG_FORM_THRESHOLD:
            long_hint.set_text("Modo artigo longo: pipeline multi-agente (com IA).")
        else:
            long_hint.set_text("")

    def refresh_preflight() -> None:
        render_brief_preflight(
            topic_getter=lambda: topic.value or "",
            keywords_getter=lambda: keywords.value or "",
            refs_getter=lambda: refs.value or "",
            word_count_getter=lambda: word_count.value or "",
            use_llm=config.use_llm,
            host=preflight_host,
        )

    def _on_brief_field_change() -> None:
        render_keyword_chips()
        update_complexity()
        refresh_preflight()

    keywords.on("update:model-value", lambda _: _on_brief_field_change())
    word_count.on("update:model-value", lambda _: _on_brief_field_change())
    topic.on("update:model-value", lambda _: refresh_preflight())
    refs.on("update:model-value", lambda _: refresh_preflight())
    update_complexity()
    render_keyword_chips()
    refresh_preflight()

    def _selected_provider() -> str | None:
        val = provider_select.value
        return None if val == "auto" else val

    def _generation_provider(use_llm: bool) -> str | None:
        if not use_llm:
            return None
        return _selected_provider() or config.provider

    def _copy_markdown() -> None:
        content = article_state.get("markdown") or ""
        if not content:
            ui.notify("Nada para copiar.", type="warning")
            return
        ui.run_javascript(f"navigator.clipboard.writeText({json.dumps(content)})")
        ui.notify("Conteúdo copiado.", type="positive")

    def render_article_result(pkg, result, meta, brief: BlogBrief) -> None:
        article_state["id"] = result.article_id
        article_state["markdown"] = pkg.markdown
        article_state["meta"] = meta
        article_state["provider"] = pkg.provider_used or (
            "IA" if pkg.used_llm else "local"
        )

        result_box.clear()
        with result_box:
            with ui.element("div").classes("geo-blog-preview-panel w-full"):
                with ui.row().classes(
                    "w-full items-center justify-between flex-wrap gap-2 mb-4"
                ):
                    ui.label("Preview da matéria").classes("geo-section-title")
                    with ui.row().classes("gap-1"):
                        ui.button(icon="content_copy", on_click=_copy_markdown).props(
                            "flat round dense"
                        ).tooltip("Copiar")
                        ui.button(
                            icon="refresh",
                            on_click=lambda: asyncio.create_task(generate()),
                        ).props("flat round dense").tooltip("Regenerar")

                render_word_count_banner(
                    actual=pkg.word_count_actual or 0,
                    target=pkg.word_count_target or brief.word_count,
                    warning=result.warning,
                )
                render_similarity_banner(result)

                wc_target = pkg.word_count_target or brief.word_count
                wc_actual = pkg.word_count_actual or 0
                wc_chip_class = (
                    "geo-chip geo-chip--warn"
                    if wc_target and wc_actual < wc_target * 0.85
                    else "geo-chip geo-chip--primary"
                )
                with ui.row().classes("gap-2 flex-wrap mb-4"):
                    ui.html(
                        f'<span class="{wc_chip_class}">'
                        f"{wc_actual:,} / {wc_target:,} palavras</span>"
                    )
                    if (
                        result.similarity_warning
                        and result.similarity_ratio is not None
                    ):
                        sim_pct = int(result.similarity_ratio * 100)
                        ui.html(
                            '<span class="geo-chip geo-chip--warn">'
                            f"⚠ ~{sim_pct}% similar à fonte</span>"
                        )
                    provider = provider_label(article_state["provider"])
                    ui.html(
                        f'<span class="geo-chip geo-chip--primary">{provider}</span>'
                    )

                article_state["preview"] = ui.markdown(
                    normalize_preview_markdown(pkg.markdown)
                ).classes("w-full")

                with ui.expansion("Editar Markdown", icon="edit").classes(
                    "w-full mt-4"
                ):
                    editor = (
                        ui.textarea(value=pkg.markdown)
                        .classes("w-full geo-blog-input")
                        .props("outlined autogrow rows=12")
                    )
                    article_state["editor"] = editor

                    def sync_preview(_e=None) -> None:
                        article_state["markdown"] = editor.value or ""
                        if article_state["preview"]:
                            article_state["preview"].set_content(
                                normalize_preview_markdown(article_state["markdown"])
                            )

                    editor.on("update:model-value", sync_preview)
                    ui.button("Atualizar preview", on_click=sync_preview).props(
                        "flat dense color=primary"
                    )

                render_geo_checklist(
                    brief,
                    pkg,
                    result,
                    checklist_state=article_state["checklist"],
                )

                with ui.tabs().classes("w-full geo-inner-tabs mt-4") as detail_tabs:
                    t_idx = ui.tab("Índice IA")
                    t_seo = ui.tab("SEO")
                    t_faq_ld = ui.tab("FAQ JSON-LD")
                    t_skel = ui.tab("Esqueleto GEO")

                with ui.tab_panels(detail_tabs, value=t_idx).classes("w-full"):
                    with ui.tab_panel(t_idx):
                        ui.code(
                            json.dumps(pkg.ai_index, indent=2, ensure_ascii=False),
                            language="json",
                        ).classes("w-full")
                        if result.index_path:
                            ui.label(f"Salvo: {result.index_path}").classes(
                                "geo-meta-caption"
                            )
                    with ui.tab_panel(t_seo):
                        ui.input(
                            "Meta title",
                            value=meta.get("meta_title", ""),
                        ).props(
                            "readonly outlined dense"
                        ).classes("w-full")
                        ui.textarea(
                            "Meta description",
                            value=meta.get("meta_description", ""),
                        ).props("readonly outlined dense").classes("w-full")
                        ui.input(
                            "Slug",
                            value=meta.get("slug", ""),
                        ).props(
                            "readonly outlined dense"
                        ).classes("w-full")
                        ui.label(
                            "Keywords: " + ", ".join(meta.get("keywords", []))
                        ).classes("text-caption")
                    with ui.tab_panel(t_faq_ld):
                        render_faq_jsonld_export(
                            faq_items=meta.get("faq") or pkg.faq_items,
                            markdown=article_state.get("markdown") or pkg.markdown,
                            page_title=meta.get("meta_title", "") or pkg.meta_title,
                            slug=meta.get("slug", "") or pkg.slug,
                        )
                        if result.faq_jsonld_path:
                            ui.label(f"Salvo: {result.faq_jsonld_path}").classes(
                                "geo-meta-caption mt-2"
                            )
                    with ui.tab_panel(t_skel):
                        ui.markdown(pkg.skeleton.markdown).classes("w-full")

                async def save_to_blog() -> None:
                    content = (
                        article_state["editor"].value
                        if article_state.get("editor")
                        else article_state["markdown"]
                    )
                    try:
                        index_payload = index_from_blog_package(pkg)
                        if meta:
                            index_payload = build_history_json_index(
                                ai_index=index_payload,
                                meta=meta,
                            )
                        save_result = await save_post_to_blog(
                            title=meta.get("meta_title", "") or pkg.meta_title,
                            markdown_content=content or "",
                            json_index=index_payload,
                            article_id=article_state["id"],
                            status=ArticleStatus.DRAFT.value,
                            user_id=require_session_user_id(),
                        )
                        article_state["id"] = save_result.article_id
                        ui.notify(
                            f"Matéria salva no blog (#{save_result.article_id}).",
                            type="positive",
                        )
                    except Exception as exc:
                        logger.exception("Falha ao salvar no blog local: %s", exc)
                        ui.notify(f"Erro ao salvar no blog: {exc}", type="negative")

                ui.button(
                    "Salvar no blog",
                    icon="save",
                    on_click=save_to_blog,
                ).props(
                    "color=primary"
                ).classes("mt-4")

    _touch_article_session()

    async def generate(force_local: bool = False) -> None:
        _touch_article_session()
        alert_box.clear()
        result_box.clear()

        wc = blog_word_count(word_count.value)
        use_llm = config.use_llm and not force_local

        preflight = evaluate_brief_preflight(
            topic=topic.value or "",
            keywords=parse_keywords(keywords.value or ""),
            reference_urls=[
                u.strip() for u in (refs.value or "").splitlines() if u.strip()
            ],
            word_count=wc,
            use_llm=use_llm,
        )
        if has_blocking_issues(preflight) or not (topic.value or "").strip():
            alert_box.clear()
            with alert_box:
                if not (topic.value or "").strip():
                    ui.label("Informe o tema principal.").classes(ALERT_WARNING)
                for item in preflight:
                    if not item.passed and (item.blocking or item.item_id == "topic"):
                        ui.label(f"{item.label}: {item.hint or item.detail}").classes(
                            ALERT_WARNING
                        )
            refresh_preflight()
            return

        alert_box.clear()

        if wc >= LONG_FORM_THRESHOLD and not use_llm:

            async def force_local_generate() -> None:
                await generate(force_local=True)

            with alert_box:
                ui.label(
                    "Artigos com 2.600+ palavras exigem IA. Ative «Gerar artigo com IA» "
                    "na sidebar ou continue em modo local."
                ).classes(ALERT_WARNING)
                ui.button(
                    "Continuar mesmo assim (rascunho local)",
                    on_click=force_local_generate,
                ).props("outline color=orange")
            return

        tone_value = blog_tone_value(tone.value)
        niche_options = geo_niche_select_options()
        brief = BlogBrief(
            topic=topic.value.strip(),
            reference_urls=[
                u.strip() for u in (refs.value or "").splitlines() if u.strip()
            ],
            target_keywords=parse_keywords(keywords.value or ""),
            audience=(audience.value or "").strip() or "Leitores interessados no tema",
            tone=tone_value,
            word_count=wc,
            brand_name=(brand.value or "").strip(),
            cta=(cta.value or "").strip(),
            include_faq=bool(include_faq.value),
            angle=(angle.value or "").strip(),
            geo_niche=niche_options.get(niche_select.value, "generic"),
        )

        gen_provider = _generation_provider(use_llm)
        owner_id = require_session_user_id()

        def _apply_blog_success(result) -> None:
            pkg = result.package
            meta = result.meta_payload
            article_state["id"] = result.article_id
            article_state["checklist"] = {"manual": {}, "complete": False}
            result_box.clear()
            with alert_box:
                if result.article_id:
                    ui.label(f"Salvo no histórico (#{result.article_id})").classes(
                        ALERT_SUCCESS,
                    )
                elif config.use_llm or pkg.markdown:
                    ui.label(
                        "Não foi possível salvar no histórico (ver logs)."
                    ).classes(
                        ALERT_WARNING,
                    )
                if result.fallback_reason:
                    ui.label(result.fallback_reason).classes(ALERT_WARNING)
                notify_word_count_if_needed(
                    actual=pkg.word_count_actual or 0,
                    target=pkg.word_count_target or wc,
                    warning=result.warning,
                )
                notify_similarity_if_needed(result)
                render_url_cache_banner(result.url_cache_message)
                if pkg.generation_mode.startswith("multi_agent"):
                    ui.label(
                        "Pipeline: multi-agente (Pesquisador → Redator → Editor)"
                    ).classes("geo-meta-caption")
            render_article_result(pkg, result, meta, brief)

        def _on_blog_failed(err: str) -> None:
            result_box.clear()
            with alert_box:
                ui.label(f"Erro ao gerar: {err}").classes(ALERT_ERROR)
            if generate_btn:
                generate_btn.enable()

        if should_queue_blog(brief, use_llm=use_llm):
            if generate_btn:
                generate_btn.disable()
            with result_box:
                tracker_host = ui.column().classes("w-full")
            job_id = get_background_job_service().submit(
                lambda report: run_blog_job(
                    report,
                    brief=brief,
                    config=config,
                    use_llm=use_llm,
                    provider=gen_provider,
                    article_id=article_state["id"],
                    user_id=owner_id,
                ),
                label=f"Matéria: {brief.topic[:48]}",
                kind=JobKind.BLOG,
            )

            def _on_blog_done(result) -> None:
                try:
                    _apply_blog_success(result)
                finally:
                    if generate_btn:
                        generate_btn.enable()

            mount_background_job_tracker(
                job_id,
                host=tracker_host,
                on_completed=_on_blog_done,
                on_failed=_on_blog_failed,
            )
            return

        if generate_btn:
            generate_btn.disable()

        with result_box:
            with ui.element("div").classes("geo-blog-preview-panel"):
                with ui.row().classes("items-center gap-3"):
                    ui.spinner(size="md").classes("geo-loading-spinner")
                    with ui.column().classes("gap-0"):
                        ui.label("A gerar a matéria…").classes("text-body2 font-medium")
                        progress_panel = AgentProgressPanel()

        try:
            if use_llm:
                result = await run_blog_pipeline_async(
                    brief,
                    use_advanced=config.use_advanced,
                    use_llm=True,
                    provider=gen_provider,
                    manager=config.ai_manager,
                    on_progress=progress_panel.build_callback(),
                    article_id=article_state["id"],
                    user_id=owner_id,
                )
            else:
                result = await run.io_bound(
                    lambda: run_blog_pipeline(
                        brief,
                        use_advanced=config.use_advanced,
                        use_llm=False,
                        provider=gen_provider,
                        manager=config.ai_manager,
                        article_id=article_state["id"],
                        user_id=owner_id,
                    )
                )
        except Exception as exc:
            logger.exception("Erro ao gerar matéria: %s", exc)
            ui.notify(f"Erro ao gerar matéria: {exc}", type="negative")
            _on_blog_failed(str(exc))
            return
        finally:
            if generate_btn:
                generate_btn.enable()

        _apply_blog_success(result)

    if generate_btn:
        generate_btn.on("click", lambda: asyncio.create_task(generate()))
