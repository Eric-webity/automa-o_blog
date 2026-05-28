"""Aba: validar JSON ChatGPT."""

from __future__ import annotations

import json

from nicegui import ui

from core.json_parser import extract_geo_signals
from ui.widgets import geo_textarea, page_header, primary_button


def build_tab_json() -> None:
    page_header(
        "Validar JSON do Network",
        "Cole o payload capturado no DevTools do ChatGPT para extrair sinais GEO.",
    )
    raw = geo_textarea("JSON do Network", rows=8)
    result_box = ui.column().classes("w-full mt-4")

    def validate() -> None:
        result_box.clear()
        sig = extract_geo_signals(raw.value or "")
        with result_box:
            if sig["valid_json"]:
                ui.label("JSON válido.").classes("geo-alert geo-alert--success")
                display = {k: v for k, v in sig.items() if k != "error"}
                ui.code(
                    json.dumps(display, indent=2, ensure_ascii=False),
                    language="json",
                ).classes("w-full")
            else:
                ui.label(sig.get("error", "JSON inválido")).classes("geo-alert geo-alert--error")

    primary_button("Validar JSON", validate, icon="data_object")
