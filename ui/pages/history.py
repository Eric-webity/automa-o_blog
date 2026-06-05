"""Rota /historico (aceita ?article=ID para abrir uma matéria)."""

from __future__ import annotations

from nicegui import ui

from ui.pages.routes import ROUTE_HISTORY
from ui.pages.shell import render_page
from ui.tab_history import build_tab_history


def register(config) -> None:
    @ui.page(ROUTE_HISTORY)
    def history_page(article: str | None = None) -> None:
        def builder(cfg) -> None:
            build_tab_history(cfg)
            if article:
                try:
                    article_id = int(article)
                except (TypeError, ValueError):
                    ui.notify(
                        f"ID de matéria inválido: «{article}».", type="warning"
                    )
                    return
                opener = getattr(cfg, "open_history_article", None)
                if opener:
                    opener(article_id)

        render_page(config, ROUTE_HISTORY, builder)
