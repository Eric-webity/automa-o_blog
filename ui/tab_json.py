"""Aba: validar JSON ChatGPT (layout Content Studio)."""

from __future__ import annotations

import json
import re
from datetime import datetime

from nicegui import ui

from core.json_parser import extract_geo_signals
from ui.constants import ALERT_ERROR, ALERT_SUCCESS, ALERT_WARNING
from ui.pages.routes import ROUTE_BLOG
from ui.widgets import page_header

_TIPS = (
    (
        "schema",
        "geo-json-tip__icon--tertiary",
        "Estrutura Hierárquica",
        'Garanta que blocos como "search_model_queries" e "search_result_groups" '
        "estejam presentes no payload.",
    ),
    (
        "data_object",
        "geo-json-tip__icon--secondary",
        "Payload ChatGPT",
        "Copie o conteúdo da resposta Network (XHR/fetch) para resultados mais granulares.",
    ),
)

_MAX_RECENT = 8


def _try_fix_json(raw: str) -> str:
    """Heurísticas simples para payloads SSE ou JSON truncado."""
    text = raw.strip()
    if not text:
        return text

    chunks: list[str] = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line == "[DONE]":
            continue
        if line.startswith("data:"):
            line = line[5:].strip()
        if line:
            chunks.append(line)

    if len(chunks) == 1:
        text = chunks[0]
    elif chunks:
        text = "".join(chunks)

    for open_ch, close_ch in (("{", "}"), ("[", "]")):
        start = text.find(open_ch)
        end = text.rfind(close_ch)
        if start != -1 and end > start:
            return text[start : end + 1]

    text = re.sub(r",\s*([}\]])", r"\1", text)
    return text


def _calc_precision(sig: dict) -> int:
    if not sig.get("valid_json"):
        return 0
    score = 25
    if sig.get("queries"):
        score += 25
    if sig.get("domains"):
        score += 25
    if sig.get("urls"):
        score += 25
    return min(100, score)


def _format_timestamp(value: datetime) -> str:
    now = datetime.now()
    diff = (now.date() - value.date()).days
    if diff == 0:
        return f"Hoje, {value.strftime('%H:%M')}"
    if diff == 1:
        return f"Ontem, {value.strftime('%H:%M')}"
    months = ("Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez")
    return f"{value.day} {months[value.month - 1]}, {value.strftime('%H:%M')}"


def _guess_label(raw: str, sig: dict) -> str:
    if sig.get("queries"):
        q = sig["queries"][0][:28]
        return f"{q}.json" if q else "payload.json"
    snippet = raw.strip()[:24].replace("\n", " ")
    if snippet:
        return f"{snippet}.json"
    return "validacao.json"


def build_tab_json(config) -> None:
    recent_items: list[dict] = []
    validate_btn: ui.button | None = None

    result_box = ui.column().classes("w-full geo-json-results")
    recent_grid = ui.element("div").classes("geo-json-recent-grid w-full")
    precision_value: ui.label | None = None
    precision_bar: ui.element | None = None
    preview_stats: ui.label | None = None

    with ui.element("div").classes("geo-json-page w-full"):
        ui.element("div").classes("geo-json-blob geo-json-blob--tr")
        ui.element("div").classes("geo-json-blob geo-json-blob--bl")

        def _json_actions() -> None:
            ui.button(
                "Novo Projeto", icon="add_circle", on_click=lambda: _new_project()
            ).props("no-caps unelevated").classes("geo-json-hero-btn")

        page_header(
            "Extração de JSON via ChatGPT",
            "Valide e processe a estrutura de dados retornada pelo assistente. "
            "Cole o payload bruto do Network para converter e extrair as "
            "propriedades geográficas mapeadas.",
            eyebrow="Validation Studio",
            actions=_json_actions,
        )

        with ui.element("div").classes("geo-json-bento"):
            with ui.element("section").classes("geo-json-panel geo-json-panel--main"):
                with ui.element("div").classes("geo-json-panel__header"):
                    with ui.element("div").classes("geo-json-panel__title-row"):
                        with ui.element("div").classes("geo-json-panel__icon"):
                            ui.icon("code")
                        ui.label("Input de Dados").classes("geo-section-title !mb-0")
                    with ui.row().classes("gap-1"):
                        ui.button(icon="delete_sweep", on_click=lambda: _clear_all()).props(
                            "flat round dense"
                        ).classes("text-grey-7").tooltip("Limpar")
                        ui.button(icon="help_outline", on_click=lambda: help_dialog.open()).props(
                            "flat round dense"
                        ).classes("text-grey-7").tooltip("Ajuda")

                ui.label("JSON do Network").classes("geo-json-field-label")
                raw_input = (
                    ui.textarea(
                        placeholder="Cole aqui o JSON bruto ou as mensagens da rede...",
                    )
                    .classes("w-full geo-json-textarea")
                    .props("outlined rows=14")
                )

                with ui.element("div").classes("geo-json-actions-row"):
                    with ui.row().classes("items-center gap-4 flex-wrap"):
                        auto_fix = ui.checkbox("Auto-corrigir erros", value=True).props("dense")
                        pretty_out = ui.checkbox("Formatar saída", value=True).props("dense")
                    validate_btn = (
                        ui.button("Validar JSON", icon="terminal")
                        .props("no-caps unelevated")
                        .classes("geo-json-validate-btn")
                    )

            with ui.element("aside").classes("geo-json-side"):
                with ui.element("section").classes("geo-json-panel geo-json-preview p-0 overflow-hidden"):
                    ui.label("Referência do Mapa").classes("geo-json-preview__label")
                    with ui.element("div").classes("geo-json-preview__visual"):
                        ui.element("div").classes("geo-json-preview__visual-bg")
                        with ui.element("div").classes("geo-json-preview__visual-overlay"):
                            with ui.column().classes("gap-0"):
                                ui.label("Extraction Preview").classes("geo-json-preview__tag")
                                ui.label("Geospatial Overlay").classes("geo-json-preview__name")
                            ui.button(icon="fullscreen").props("flat round dense").classes(
                                "geo-json-preview__fs-btn"
                            )
                    with ui.element("div").classes("geo-json-preview__footer"):
                        with ui.row().classes("w-full justify-between items-center mb-2"):
                            ui.label("Extrações detectadas").classes("geo-json-preview__stats-label")
                            precision_value = ui.label("0% Precisão").classes("geo-json-preview__pct")
                        with ui.element("div").classes("geo-json-preview__bar"):
                            precision_bar = ui.element("div").classes("geo-json-preview__bar-fill")
                        preview_stats = ui.label("Aguardando validação").classes(
                            "geo-json-preview__stats"
                        )

                with ui.element("section").classes("geo-json-panel geo-json-tips"):
                    ui.label("Dicas de Extração").classes("geo-section-title mb-4")
                    with ui.column().classes("w-full gap-3"):
                        for icon, icon_cls, title, desc in _TIPS:
                            with ui.element("div").classes("geo-json-tip"):
                                with ui.element("div").classes(f"geo-json-tip__icon {icon_cls}"):
                                    ui.icon(icon)
                                with ui.column().classes("gap-0 min-w-0"):
                                    ui.label(title).classes("geo-json-tip__title")
                                    ui.label(desc).classes("geo-json-tip__desc")

        result_box

        with ui.element("section").classes("geo-json-recent-section"):
            with ui.row().classes("w-full justify-between items-center mb-4"):
                ui.label("Validações Recentes").classes("geo-section-title !mb-0")
                ui.button("Ver tudo", icon="chevron_right", on_click=lambda: None).props(
                    "flat no-caps dense"
                ).classes("geo-json-recent-link")
            recent_grid

        ui.label("© GEO Extractor Studio • Validação de payload Network").classes(
            "geo-json-footer"
        )

    with ui.dialog() as help_dialog, ui.card().classes("geo-json-help-dialog"):
        ui.label("Como validar o JSON").classes("text-h6")
        ui.markdown(
            "1. Abra o ChatGPT no navegador e a aba **Network** (DevTools).\n"
            "2. Dispare uma busca ou resposta que inclua dados GEO.\n"
            "3. Copie o corpo da requisição/resposta JSON e cole no campo principal.\n"
            "4. Use **Auto-corrigir** para payloads SSE ou JSON parcial.\n"
            "5. Clique em **Validar JSON** para extrair queries, domínios e URLs."
        ).classes("text-body2")
        ui.button("Entendi", on_click=help_dialog.close).props("flat no-caps color=primary")

    def _update_preview(sig: dict) -> None:
        if not precision_value or not precision_bar or not preview_stats:
            return
        pct = _calc_precision(sig)
        precision_value.set_text(f"{pct}% Precisão")
        precision_bar.style(f"width: {pct}%")
        if not sig.get("valid_json"):
            preview_stats.set_text(sig.get("error") or "JSON inválido")
            return
        parts = []
        if sig.get("queries"):
            parts.append(f"{len(sig['queries'])} queries")
        if sig.get("domains"):
            parts.append(f"{len(sig['domains'])} domínios")
        if sig.get("urls"):
            parts.append(f"{len(sig['urls'])} URLs")
        preview_stats.set_text(
            " • ".join(parts) if parts else "JSON válido, sem sinais GEO detectados"
        )

    def _render_recent() -> None:
        recent_grid.clear()
        with recent_grid:
            if not recent_items:
                ui.label("Nenhuma validação nesta sessão.").classes(
                    "geo-json-recent-empty text-caption text-grey-7"
                )
                return
            for item in recent_items[:4]:
                status = item["status"]
                badge_cls = (
                    "geo-json-recent-card__badge--ok"
                    if status == "ok"
                    else "geo-json-recent-card__badge--err"
                )
                badge_text = "SUCESSO" if status == "ok" else "ERRO"
                with ui.element("div").classes("geo-json-recent-card").on(
                    "click", lambda _e, payload=item["raw"]: _load_recent(payload)
                ):
                    with ui.row().classes("w-full justify-between items-start mb-3"):
                        with ui.element("div").classes("geo-json-recent-card__icon-wrap"):
                            ui.icon("description")
                        ui.html(
                            f'<span class="geo-json-recent-card__badge {badge_cls}">'
                            f"{badge_text}</span>"
                        )
                    ui.label(item["label"]).classes("geo-json-recent-card__title")
                    ui.label(item["when"]).classes("geo-json-recent-card__meta")

    def _load_recent(payload: str) -> None:
        raw_input.value = payload
        validate()

    def _clear_all() -> None:
        raw_input.value = ""
        result_box.clear()
        _update_preview({"valid_json": False, "error": "Aguardando validação"})

    def _new_project() -> None:
        _clear_all()
        ui.navigate.to(ROUTE_BLOG)

    def _push_recent(raw: str, sig: dict) -> None:
        recent_items.insert(
            0,
            {
                "label": _guess_label(raw, sig),
                "when": _format_timestamp(datetime.now()),
                "status": "ok" if sig.get("valid_json") else "err",
                "raw": raw,
            },
        )
        del recent_items[_MAX_RECENT:]
        _render_recent()

    def validate() -> None:
        result_box.clear()
        text = raw_input.value or ""

        if not text.strip():
            with result_box:
                ui.label("Por favor, insira um JSON para validar.").classes(
                    ALERT_WARNING
                )
            _update_preview({"valid_json": False, "error": "Nenhum conteúdo informado"})
            return

        if auto_fix.value:
            text = _try_fix_json(text)
            raw_input.value = text

        sig = extract_geo_signals(text)
        _update_preview(sig)
        _push_recent(text, sig)

        with result_box:
            if sig["valid_json"]:
                ui.label("JSON válido — sinais GEO extraídos.").classes(
                    ALERT_SUCCESS
                )
                display = {k: v for k, v in sig.items() if k != "error"}
                indent = 2 if pretty_out.value else None
                ui.code(
                    json.dumps(display, indent=indent, ensure_ascii=False),
                    language="json",
                ).classes("w-full geo-json-code")
            else:
                ui.label(sig.get("error", "JSON inválido")).classes(ALERT_ERROR)

    if validate_btn:
        validate_btn.on("click", validate)

    _update_preview({"valid_json": False, "error": "Aguardando validação"})
    _render_recent()
