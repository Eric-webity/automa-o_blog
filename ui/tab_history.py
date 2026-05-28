"""Aba: histórico de matérias do blog local."""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime

from nicegui import run, ui

from db.models import ArticleStatus
from db.repository import ArticleRecord, ArticleRepository
from services.blog_publisher import save_post_to_blog
from ui.components.article_split_view import ArticleSplitView
from ui.widgets import page_header

logger = logging.getLogger(__name__)


def _format_date(value: datetime) -> str:
    """Formata data para exibição na lista."""
    if value.tzinfo:
        value = value.replace(tzinfo=None)
    return value.strftime("%d/%m/%Y %H:%M")


def build_tab_history(config) -> None:
    """Lista matérias salvas com reabrir, atualizar e excluir."""
    page_header(
        "Histórico do blog",
        "Matérias salvas no Content Studio. Reabra, edite e atualize no blog local.",
    )

    list_container = ui.column().classes("w-full gap-2")
    detail_container = ui.column().classes("w-full mt-4")

    def clear_detail() -> None:
        detail_container.clear()

    def show_article(record: ArticleRecord) -> None:
        """Exibe matéria selecionada com abas Artigo e Índice IA."""
        clear_detail()
        with detail_container:
            ui.label(record.title).classes("text-subtitle1 font-medium")
            ui.label(f"#{record.id} · {record.status} · {_format_date(record.created_at)}").classes(
                "text-caption text-grey-7 mb-2"
            )
            with ui.tabs().classes("w-full") as detail_tabs:
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
                        """Atualiza conteúdo editado no histórico local."""
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
                            logger.exception("Falha ao atualizar matéria no blog: %s", exc)
                            ui.notify(f"Erro ao salvar no blog: {exc}", type="negative")

                    async def mark_completed() -> None:
                        """Marca matéria como concluída."""
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
                            logger.exception("Falha ao marcar matéria como concluída: %s", exc)
                            ui.notify(f"Erro: {exc}", type="negative")

                    with ui.row().classes("gap-2 mt-3"):
                        ui.button(
                            "Atualizar no blog",
                            on_click=update_in_blog,
                        ).props("color=primary icon=save")
                        ui.button(
                            "Marcar como concluída",
                            on_click=mark_completed,
                        ).props("outline")

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

    async def refresh_list() -> None:
        """Recarrega lista a partir do SQLite."""
        try:
            list_container.clear()
            clear_detail()
            records = await run.io_bound(ArticleRepository().list_all)
        except RuntimeError:
            # A aba pode ter sido removida durante transição de tabs.
            return
        except Exception as exc:
            logger.exception("Erro ao carregar histórico: %s", exc)
            ui.notify(f"Erro ao carregar histórico: {exc}", type="negative")
            return

        if not records:
            with list_container:
                ui.label("Nenhuma matéria salva ainda.").classes("text-grey-7")
            return

        with list_container:
            for record in records:
                with ui.card().classes("w-full"):
                    with ui.row().classes("w-full items-center justify-between"):
                        with ui.column().classes("gap-0"):
                            ui.label(record.title).classes("font-medium")
                            ui.label(
                                f"{_format_date(record.created_at)} · {record.status}"
                            ).classes("text-caption text-grey-7")
                        with ui.row().classes("gap-2"):
                            ui.button(
                                "Reabrir",
                                on_click=lambda r=record: show_article(r),
                            ).props("flat color=primary")
                            ui.button(
                                "Excluir",
                                on_click=lambda r=record: delete_article(r),
                            ).props("flat color=negative")

    async def delete_article(record: ArticleRecord) -> None:
        """Remove matéria do histórico local."""
        try:
            deleted = await run.io_bound(ArticleRepository().delete, record.id)
        except Exception as exc:
            logger.exception("Erro ao excluir artigo id=%s: %s", record.id, exc)
            ui.notify(f"Erro ao excluir: {exc}", type="negative")
            return
        if deleted:
            ui.notify("Matéria removida do histórico.", type="positive")
            await refresh_list()
        else:
            ui.notify("Matéria não encontrada.", type="warning")

    def open_article_by_id(article_id: int) -> None:
        """Abre matéria por ID (atalho a partir do dashboard)."""
        record = ArticleRepository().get_by_id(article_id)
        if record:
            show_article(record)
        else:
            ui.notify("Matéria não encontrada.", type="warning")

    config.open_history_article = open_article_by_id

    ui.button("Atualizar lista", on_click=refresh_list).props("outline no-caps").classes(
        "mb-4 geo-btn-outline"
    )
    asyncio.create_task(refresh_list())
