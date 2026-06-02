"""Aba: histórico de matérias do blog local (layout Content Studio)."""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime

from nicegui import run, ui

from db.models import ArticleStatus
from db.repository import ArticleRecord, ArticleRepository
from services.analytics import get_dashboard_stats
from services.blog_publisher import save_post_to_blog
from ui.components.article_split_view import ArticleSplitView
from ui.constants import history_status_pill_html
from ui.pages.routes import ROUTE_URLS
from ui.widgets import page_header

logger = logging.getLogger(__name__)

_STORAGE_QUOTA_BYTES = 100 * 1024 * 1024


def _format_date(value: datetime) -> str:
    if value.tzinfo:
        value = value.replace(tzinfo=None)
    return value.strftime("%d/%m/%Y %H:%M")


def _format_saved_time(minutes: int) -> str:
    if minutes <= 0:
        return "0h 0m"
    hours, mins = divmod(minutes, 60)
    if hours:
        return f"{hours}h {mins}m"
    return f"{mins}m"


def build_tab_history(config) -> None:
    """Lista matérias salvas com reabrir, atualizar e excluir."""
    stats_container = ui.element("div").classes("geo-history-stats-grid w-full")
    main_container = ui.element("div").classes("geo-history-main w-full")
    detail_container = ui.column().classes("w-full")
    active_id: dict[str, int | None] = {"id": None}
    last_records: list[ArticleRecord] = []

    search_ref: dict = {"el": None}

    def _history_actions() -> None:
        with ui.row().classes("geo-history-search items-center"):
            ui.icon("search").classes("text-grey-6")
            search_ref["el"] = (
                ui.input(placeholder="Pesquisar histórico…")
                .props("borderless dense")
                .classes("flex-grow")
            )

    with ui.element("div").classes("geo-history-page w-full"):
        page_header(
            "Histórico do blog",
            "Reabra, atualize ou exporte as matérias guardadas no blog local.",
            eyebrow="Biblioteca",
            actions=_history_actions,
        )
        search_input = search_ref["el"]

        stats_container
        main_container

        with ui.element("div").classes("geo-history-tips-grid w-full"):
            with ui.element("div").classes("geo-history-tip-card"):
                with ui.element("div").classes(
                    "geo-history-tip-card__icon geo-history-tip-card__icon--primary"
                ):
                    ui.icon("lightbulb")
                with ui.column().classes("gap-0"):
                    ui.html("<h3>Dica de extração</h3>")
                    ui.html(
                        "<p>Use links diretos de blogs para garantir que a IA capture "
                        "toda a semântica do texto original.</p>"
                    )
            with ui.element("div").classes("geo-history-tip-card"):
                with ui.element("div").classes(
                    "geo-history-tip-card__icon geo-history-tip-card__icon--secondary"
                ):
                    ui.icon("auto_fix_high")
                with ui.column().classes("gap-0"):
                    ui.html("<h3>Poder da IA</h3>")
                    ui.html(
                        "<p>A ferramenta converte URLs e textos em estruturas JSON "
                        "prontas para publicação no blog local.</p>"
                    )

        detail_container

    def clear_detail() -> None:
        detail_container.clear()
        active_id["id"] = None

    def render_stats(data: dict) -> None:
        total = data.get("total_articles", 0)
        llm_count = data.get("llm_articles", 0)
        storage_bytes = data.get("storage_db_bytes", 0) + data.get("storage_output_bytes", 0)
        storage_label = data.get("storage_db_label", "0 B")
        storage_pct = min(100, int(storage_bytes / _STORAGE_QUOTA_BYTES * 100))

        stats_container.clear()
        with stats_container:
            with ui.element("div").classes("geo-history-stat-card"):
                ui.label("Total extraído").classes("geo-history-stat-card__label")
                with ui.element("div").classes("geo-history-stat-card__row"):
                    ui.label(str(total)).classes(
                        "geo-history-stat-card__value geo-history-stat-card__value--primary"
                    )
                    ui.label("materiais").classes("geo-history-stat-card__suffix")

            with ui.element("div").classes("geo-history-stat-card"):
                ui.label("Processamento IA").classes("geo-history-stat-card__label")
                with ui.element("div").classes("geo-history-stat-card__row"):
                    ui.label(_format_saved_time(llm_count * 5)).classes(
                        "geo-history-stat-card__value geo-history-stat-card__value--secondary"
                    )
                    ui.label("tempo estimado").classes("geo-history-stat-card__suffix")

            with ui.element("div").classes("geo-history-stat-card"):
                ui.label("Armazenamento").classes("geo-history-stat-card__label")
                with ui.element("div").classes("geo-history-stat-card__row"):
                    ui.label(f"{storage_pct}%").classes(
                        "geo-history-stat-card__value geo-history-stat-card__value--tertiary"
                    )
                    ui.label(storage_label).classes("geo-history-stat-card__suffix")

    def show_article(record: ArticleRecord) -> None:
        active_id["id"] = record.id
        detail_container.clear()
        with detail_container:
            with ui.element("div").classes("geo-history-detail w-full"):
                with ui.row().classes("w-full items-start justify-between flex-wrap gap-2 mb-2"):
                    with ui.column().classes("gap-0"):
                        ui.label(record.title).classes("text-h6 font-medium")
                        ui.label(
                            f"#{record.id} · {_format_date(record.created_at)}"
                        ).classes("text-caption text-grey-7")
                    ui.html(history_status_pill_html(record.status))

                with ui.tabs().classes("w-full geo-inner-tabs") as detail_tabs:
                    t_art = ui.tab("Artigo")
                    t_idx = ui.tab("Índice IA")

                with ui.tab_panels(detail_tabs, value=t_art).classes("w-full"):
                    with ui.tab_panel(t_art):
                        split_view = ArticleSplitView(
                            record.markdown_content,
                            footer=f"Blog local · matéria #{record.id}",
                            live_preview=True,
                        )

                        async def update_in_blog() -> None:
                            try:
                                result = await save_post_to_blog(
                                    title=record.title,
                                    markdown_content=split_view.content,
                                    json_index=record.json_index,
                                    article_id=record.id,
                                    status=record.status,
                                )
                                ui.notify(
                                    f"Matéria #{result.article_id} atualizada no blog.",
                                    type="positive",
                                )
                                await refresh_list()
                            except Exception as exc:
                                logger.exception("Falha ao atualizar matéria: %s", exc)
                                ui.notify(f"Erro ao salvar no blog: {exc}", type="negative")

                        async def mark_completed() -> None:
                            try:
                                await save_post_to_blog(
                                    title=record.title,
                                    markdown_content=split_view.content,
                                    json_index=record.json_index,
                                    article_id=record.id,
                                    status=ArticleStatus.COMPLETED.value,
                                )
                                ui.notify("Matéria marcada como concluída.", type="positive")
                                await refresh_list()
                            except Exception as exc:
                                logger.exception("Falha ao concluir matéria: %s", exc)
                                ui.notify(f"Erro: {exc}", type="negative")

                        with ui.row().classes("gap-2 mt-3"):
                            ui.button("Atualizar no blog", on_click=update_in_blog).props(
                                "color=primary icon=save"
                            )
                            ui.button("Marcar como concluída", on_click=mark_completed).props(
                                "outline"
                            )

                    with ui.tab_panel(t_idx):
                        if record.json_index:
                            ui.code(
                                json.dumps(record.json_index, indent=2, ensure_ascii=False),
                                language="json",
                            ).classes("w-full")
                        else:
                            ui.label("Sem índice IA salvo para esta matéria.").classes(
                                "text-caption text-grey-7"
                            )

        if last_records:
            render_article_list(last_records)

    def render_empty_state() -> None:
        main_container.clear()
        with main_container:
            with ui.element("div").classes("geo-history-panel geo-history-panel--empty"):
                ui.element("div").classes("geo-history-panel__blob geo-history-panel__blob--tr")
                ui.element("div").classes("geo-history-panel__blob geo-history-panel__blob--bl")
                with ui.element("div").classes("geo-history-empty"):
                    with ui.element("div").classes("geo-history-empty__icon"):
                        ui.icon("inventory_2", size="xl")
                    ui.label("Nada por aqui ainda").classes("geo-history-empty__title")
                    ui.label(
                        "Seu histórico de materiais salvos está vazio. Comece a extrair "
                        "conteúdo para gerenciar suas postagens aqui."
                    ).classes("geo-history-empty__desc")
                    with ui.element("div").classes("geo-history-empty__actions"):
                        ui.button(
                            "Atualizar lista",
                            icon="refresh",
                            on_click=refresh_list,
                        ).classes("geo-history-refresh-btn")
                        ui.button(
                            "Ir para URLs",
                            on_click=lambda: ui.navigate.to(ROUTE_URLS),
                        ).classes("geo-history-secondary-btn")

    def render_article_list(records: list[ArticleRecord]) -> None:
        main_container.clear()
        with main_container:
            with ui.element("div").classes("geo-history-panel"):
                ui.element("div").classes("geo-history-panel__blob geo-history-panel__blob--tr")
                with ui.row().classes("w-full items-center justify-between mb-4 relative z-10"):
                    ui.label(f"{len(records)} matéria(s)").classes("geo-section-title")
                    ui.button(
                        "Atualizar lista",
                        icon="refresh",
                        on_click=refresh_list,
                    ).props("flat dense color=primary")

                with ui.element("div").classes("geo-history-list"):
                    for record in records:
                        words = len((record.markdown_content or "").split())
                        is_active = active_id["id"] == record.id
                        item_cls = (
                            "geo-history-item geo-history-item--active"
                            if is_active
                            else "geo-history-item"
                        )

                        with ui.row().classes(f"{item_cls} w-full items-center"):
                            with ui.column().classes("gap-0 flex-grow min-w-0 cursor-pointer").on(
                                "click", lambda _e, r=record: show_article(r)
                            ):
                                ui.label(record.title).classes("geo-history-item__title")
                                ui.label(
                                    f"#{record.id} · {_format_date(record.created_at)} · "
                                    f"{words} palavras · {record.status}"
                                ).classes("geo-history-item__meta")
                            with ui.row().classes("gap-1 flex-shrink-0"):
                                ui.button(
                                    icon="open_in_new",
                                    on_click=lambda _e, r=record: show_article(r),
                                ).props("flat round dense color=primary")
                                ui.button(
                                    icon="delete",
                                    on_click=lambda _e, r=record: asyncio.create_task(
                                        delete_article(r)
                                    ),
                                ).props("flat round dense color=negative")

    async def refresh_list() -> None:
        try:
            data = await run.io_bound(get_dashboard_stats)
            records = await run.io_bound(ArticleRepository().list_all)
        except RuntimeError:
            return
        except Exception as exc:
            logger.exception("Erro ao carregar histórico: %s", exc)
            ui.notify(f"Erro ao carregar histórico: {exc}", type="negative")
            return

        render_stats(data)

        query = (search_input.value or "").strip().lower()
        if query:
            records = [r for r in records if query in (r.title or "").lower()]

        if not records:
            render_empty_state()
            clear_detail()
            last_records.clear()
            return

        last_records.clear()
        last_records.extend(records)
        render_article_list(records)

        if active_id["id"] is not None:
            match = next((r for r in records if r.id == active_id["id"]), None)
            if not match:
                clear_detail()

    async def delete_article(record: ArticleRecord) -> None:
        try:
            deleted = await run.io_bound(ArticleRepository().delete, record.id)
        except Exception as exc:
            logger.exception("Erro ao excluir artigo id=%s: %s", record.id, exc)
            ui.notify(f"Erro ao excluir: {exc}", type="negative")
            return
        if deleted:
            ui.notify("Matéria removida do histórico.", type="positive")
            if active_id["id"] == record.id:
                clear_detail()
            await refresh_list()
        else:
            ui.notify("Matéria não encontrada.", type="warning")

    def open_article_by_id(article_id: int) -> None:
        record = ArticleRepository().get_by_id(article_id)
        if record:
            show_article(record)
            asyncio.create_task(refresh_list())
        else:
            ui.notify("Matéria não encontrada.", type="warning")

    config.open_history_article = open_article_by_id
    search_input.on("update:model-value", lambda _: asyncio.create_task(refresh_list()))

    asyncio.create_task(refresh_list())
