"""Rota /lote — geração em massa via CSV."""

from __future__ import annotations

from nicegui import ui

from ui.pages.routes import ROUTE_BATCH
from ui.pages.shell import render_page
from ui.tab_batch import build_tab_batch


def register(config) -> None:
    @ui.page(ROUTE_BATCH)
    def batch_page() -> None:
        render_page(config, ROUTE_BATCH, build_tab_batch)
