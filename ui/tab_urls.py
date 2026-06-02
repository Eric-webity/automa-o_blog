"""Aba: processar URLs com layout Content Studio."""

from __future__ import annotations

import json
from datetime import date, datetime

from nicegui import run, ui

from core.insight_extractor import extract_insights, merge_insights
from db.models import ArticleStatus
from db.repository import ArticleRepository
from services.article_fetcher import MAX_WORKERS, TIMEOUT, fetch_many_with_stats
from services.blog_publisher import save_post_to_blog
from services.browser_fetcher import browser_fetch_enabled, is_playwright_installed
from services.url_pipeline import run_url_pipeline
from ui.components.article_split_view import ArticleSplitView
from ui.constants import ALERT_ERROR, ALERT_SUCCESS, ALERT_WARNING
from ui.widgets import loading_status, page_header

_TIPS = (
    "Pule linhas vazias para evitar erros no processamento em massa.",
    "Certifique-se de que os protocolos (http/https) estão incluídos.",
    "A IA GEO Extractor identificará automaticamente a estrutura do site.",
)

_RECENT_ICONS = (
    ("data_object", "geo-recent-card__icon--violet"),
    ("map", "geo-recent-card__icon--teal"),
    ("apartment", "geo-recent-card__icon--primary"),
    ("article", "geo-recent-card__icon--violet"),
)


def _relative_date(value: datetime) -> str:
    if value.tzinfo:
        value = value.replace(tzinfo=None)
    diff = (date.today() - value.date()).days
    if diff == 0:
        return f"Hoje {value.strftime('%H:%M')}"
    if diff == 1:
        return "Ontem"
    if diff == 2:
        return "2 dias atrás"
    return value.strftime("%d/%m/%Y")


def _count_url_lines(text: str | None) -> int:
    return len([line for line in (text or "").splitlines() if line.strip()])


def build_tab_urls(config) -> None:
    alert_box = ui.column().classes("w-full geo-urls-results")
    result_box = ui.column().classes("w-full geo-urls-results")
    recent_box = ui.element("div").classes("geo-recent-grid w-full")
    process_btn: ui.button | None = None
    save_state: dict = {"article_id": None}

    with ui.element("div").classes("geo-urls-page w-full"):
        page_header(
            "Processar URLs",
            "Cole links de referência para extrair insights, gerar índice IA e artigo GEO.",
            eyebrow="Extração",
        )
        with ui.element("div").classes("geo-urls-grid"):
            with ui.element("div").classes("geo-urls-main"):
                with ui.element("section").classes("geo-urls-panel w-full"):
                    with ui.element("div").classes("geo-urls-panel__header"):
                        with ui.element("div").classes("geo-urls-panel__title-row"):
                            with ui.element("div").classes("geo-urls-panel__icon"):
                                ui.icon("link")
                            with ui.column().classes("gap-0"):
                                ui.label("Lista de URLs").classes("geo-section-title")
                                ui.label(
                                    "Insira os links para extração de dados geográficos"
                                ).classes("geo-section-desc !mt-0")
                        ui.html('<span class="geo-urls-badge">Modo Lote</span>')

                    with ui.element("div").classes("geo-url-input-wrap"):
                        urls_input = (
                            ui.textarea(
                                placeholder=(
                                    "https://exemplo.com/local-1\n"
                                    "https://exemplo.com/local-2\n"
                                    "https://exemplo.com/local-3"
                                ),
                            )
                            .classes("w-full geo-url-textarea")
                            .props("outlined rows=12")
                        )
                        with ui.row().classes("geo-url-input-toolbar"):
                            ui.button(
                                "Limpar",
                                icon="delete",
                                on_click=lambda: clear_urls(),
                            ).props("flat dense no-caps").classes("text-grey-7")
                            line_count_label = ui.label("0 linhas").classes("geo-url-line-count")

                    with ui.element("div").classes("geo-urls-process-row"):
                        with ui.button(on_click=lambda: None).props("no-caps unelevated").classes(
                            "geo-urls-process-btn"
                        ) as btn:
                            process_btn = btn
                            with ui.row().classes("items-center gap-3 no-wrap"):
                                ui.label("Processar URLs")
                                with ui.element("div").classes("geo-urls-process-btn__icon"):
                                    ui.icon("play_arrow")

            with ui.element("div").classes("geo-urls-side"):
                with ui.element("section").classes("geo-urls-panel geo-quick-settings w-full"):
                    ui.label("Configurações Rápidas").classes("geo-section-title mb-4")
                    with ui.column().classes("w-full gap-3"):
                        with ui.element("div").classes("geo-quick-stat"):
                            ui.label("Threads Máximas")
                            ui.html(f"<strong>{MAX_WORKERS}</strong>")
                        with ui.element("div").classes("geo-quick-stat"):
                            ui.label("Timeout HTTP (s)")
                            ui.html(f"<strong>{TIMEOUT}</strong>")
                        with ui.element("div").classes("geo-quick-stat"):
                            browser_on = browser_fetch_enabled() and is_playwright_installed()
                            ui.label("Navegador headless")
                            ui.html(
                                f"<strong>{'Ativo (JS)' if browser_on else 'Indisponível'}</strong>"
                            )
                        with ui.element("div").classes("geo-quick-stat"):
                            ui.label("Extração avançada")
                            ui.html(
                                f"<strong>{'Sim' if config.use_advanced else 'Não'}</strong>"
                            )
                        with ui.element("div").classes("geo-quick-stat"):
                            ui.label("Gerar com IA")
                            ui.html(f"<strong>{'Sim' if config.use_llm else 'Não'}</strong>")

                with ui.element("section").classes("geo-urls-panel w-full"):
                    ui.label("Dicas Pro").classes(
                        "text-primary text-xs font-semibold uppercase tracking-widest mb-4"
                    )
                    with ui.element("ul").classes("geo-tip-list"):
                        for tip in _TIPS:
                            with ui.element("li").classes("geo-tip-item"):
                                with ui.element("div").classes("geo-tip-item__icon"):
                                    ui.icon("check", size="sm")
                                ui.html(f"<p>{tip}</p>")

        with ui.element("section").classes("mt-8 w-full"):
            with ui.element("div").classes("geo-urls-recent-header"):
                ui.label("Histórico Recente").classes("geo-section-title")
                ui.button(
                    "Ver todos",
                    icon="arrow_forward",
                    on_click=config.go_history_tab,
                ).props("flat dense no-caps color=primary")

            recent_box

    def _update_line_count() -> None:
        line_count_label.text = f"{_count_url_lines(urls_input.value)} linhas"

    def clear_urls() -> None:
        urls_input.value = ""
        _update_line_count()

    urls_input.on("update:model-value", lambda _: _update_line_count())

    def render_recent() -> None:
        recent_box.clear()
        records = ArticleRepository().list_recent(4)
        if not records:
            with recent_box:
                ui.label("Nenhuma matéria salva ainda.").classes("text-grey-7")
            return

        with recent_box:
            for index, record in enumerate(records):
                icon_name, icon_cls = _RECENT_ICONS[index % len(_RECENT_ICONS)]
                words = len((record.markdown_content or "").split())
                progress = 100 if record.status == "completed" else 60

                def open_article(_e, article_id=record.id) -> None:
                    config.open_article_in_history(article_id)

                with ui.element("div").classes("geo-recent-card").on("click", open_article):
                    with ui.element("div").classes("geo-recent-card__top"):
                        with ui.element("div").classes(f"geo-recent-card__icon {icon_cls}"):
                            ui.icon(icon_name)
                        ui.label(_relative_date(record.created_at)).classes("geo-recent-card__time")
                    ui.label(record.title).classes("geo-recent-card__title")
                    ui.label(f"{words} palavras · {record.status}").classes("geo-recent-card__meta")
                    with ui.element("div").classes("geo-recent-card__bar"):
                        ui.element("div").classes("geo-recent-card__bar-fill").style(
                            f"width: {progress}%"
                        )

    async def _persist_to_history(result) -> None:
        """Salva/atualiza a matéria gerada no histórico (banco), reutilizando o id."""
        title = (
            result.merged.get("tema_central")
            or result.merged.get("entidade_intencao")
            or "Matéria gerada a partir de URLs"
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
        urls = [u.strip() for u in (urls_input.value or "").splitlines() if u.strip()]
        if not urls:
            with alert_box:
                ui.label("Informe pelo menos uma URL.").classes(ALERT_WARNING)
            return

        if process_btn:
            process_btn.disable()

        with result_box:
            loading_status("A buscar matérias…")

        try:
            fetched, fetch_stats = await run.io_bound(fetch_many_with_stats, urls)
            warnings = [f"{a.url}: {a.error}" for a in fetched if a.error]
            cache_msg = fetch_stats.summary_message()

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
                    ui.label("Nenhuma matéria processada.").classes(ALERT_ERROR)
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
                if cache_msg:
                    ui.label(cache_msg).classes(ALERT_SUCCESS)
                for w in warnings:
                    ui.label(w).classes("geo-meta-caption")
                if result.fallback_reason:
                    ui.label(result.fallback_reason).classes(ALERT_WARNING)

            with result_box:
                ui.label(f"{len(insights_list)} matéria(s) processada(s).").classes(
                    ALERT_SUCCESS
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

            await _persist_to_history(result)
            render_recent()
        finally:
            if process_btn:
                process_btn.enable()

    if process_btn:
        process_btn.on("click", process)

    render_recent()
