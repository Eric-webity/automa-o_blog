"""Aba: lote CSV → vários Markdown em output/."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from nicegui import run, ui

from config.paths import OUTPUT_DIR, ROOT
from config.production import load_production_settings
from services.background_jobs import (
    JobKind,
    get_background_job_service,
    run_batch_job,
    should_queue_batch,
)
from services.batch_csv import (
    CSV_TEMPLATE,
    BatchDefaults,
    parse_csv_text,
    run_batch,
)
from services.webhook_notifier import notify_batch_completed
from ui.auth import require_session_user_id
from ui.components.background_job_panel import mount_background_job_tracker
from ui.constants import (
    ALERT_ERROR,
    ALERT_SUCCESS,
    ALERT_WARNING,
    BLOG_WORD_COUNT_DEFAULT,
    geo_niche_select_options,
    provider_select_options,
)
from ui.widgets import page_header

logger = logging.getLogger(__name__)

_TEMPLATE_PATH = ROOT / "samples" / "batch_template.csv"
_BATCH_TIPS = (
    "Coluna obrigatória: tema (ou topic / título).",
    "URLs de referência: separe com | ou ; na mesma célula.",
    "Cada linha gera um .md em output/batch_AAAAMMDD_HHMMSS/.",
    "Use --no-llm na CLI para rascunhos rápidos sem API.",
)


def build_tab_batch(config) -> None:
    """Constrói a página Lote CSV (upload → pré-visualização → geração)."""
    state: dict = {"specs": [], "warnings": [], "csv_name": ""}
    w: dict = {}

    alert_box = ui.column().classes("w-full geo-batch-results")
    preview_box = ui.column().classes("w-full geo-batch-preview")
    result_box = ui.column().classes("w-full geo-batch-results")

    niche_options = geo_niche_select_options()
    niche_labels = list(niche_options.keys())
    provider_options = provider_select_options(config.ready_providers or [])

    def _batch_defaults() -> BatchDefaults:
        return BatchDefaults(
            word_count=int(w["default_wc"].value or BLOG_WORD_COUNT_DEFAULT),
            geo_niche=niche_options.get(w["default_niche"].value, "generic"),
            use_llm=bool(w["use_llm"].value),
        )

    def clear_upload() -> None:
        state["specs"] = []
        state["warnings"] = []
        state["csv_name"] = ""
        preview_box.clear()
        alert_box.clear()
        result_box.clear()
        bar = w.get("progress_bar")
        label = w.get("progress_label")
        if bar:
            bar.value = 0
            bar.visible = False
        if label:
            label.visible = False

    def render_preview() -> None:
        preview_box.clear()
        specs = state["specs"]
        if not specs:
            with preview_box:
                ui.label("Envie um CSV para ver as linhas.").classes("geo-meta-caption")
            return
        with preview_box:
            ui.label(
                f"{len(specs)} matéria(s) · ficheiro: {state['csv_name'] or '—'}"
            ).classes("geo-section-desc mb-2")
            for spec in specs[:8]:
                urls_n = len(spec.brief.reference_urls)
                ui.html(
                    "<div class='geo-batch-preview-row'>"
                    f"<strong>#{spec.row_num}</strong> {spec.topic[:72]}"
                    f"<span class='geo-meta-caption'> · {spec.file_slug}.md"
                    f"{f' · {urls_n} URL(s)' if urls_n else ''}</span></div>"
                )
            if len(specs) > 8:
                ui.label(f"… e mais {len(specs) - 8} linha(s).").classes("geo-meta-caption")

    async def on_csv_upload(e) -> None:
        alert_box.clear()
        result_box.clear()
        try:
            raw = e.content.read()
            text = raw if isinstance(raw, str) else raw.decode("utf-8-sig")
            specs, warnings = await run.io_bound(
                parse_csv_text, text, defaults=_batch_defaults()
            )
            state["specs"] = specs
            state["warnings"] = warnings
            state["csv_name"] = e.name or "upload.csv"
            with alert_box:
                ui.label(f"CSV carregado: {len(specs)} linha(s) válida(s).").classes(
                    ALERT_SUCCESS
                )
                for msg in warnings[:6]:
                    ui.label(msg).classes("geo-meta-caption")
                if len(warnings) > 6:
                    ui.label(f"… +{len(warnings) - 6} aviso(s).").classes("geo-meta-caption")
            render_preview()
        except Exception as exc:
            state["specs"] = []
            state["warnings"] = []
            logger.exception("Falha ao ler CSV: %s", exc)
            with alert_box:
                ui.label(f"Erro no CSV: {exc}").classes(ALERT_ERROR)
            render_preview()

    def _render_batch_result(result) -> None:
        result_box.clear()
        with result_box:
            cls = ALERT_SUCCESS if result.failed == 0 else ALERT_WARNING
            ui.label(
                f"Lote concluído: {result.succeeded}/{result.total} gerado(s), "
                f"{result.failed} falha(s)."
            ).classes(cls)
            ui.label(f"Pasta: {result.output_dir}").classes("geo-meta-caption mb-3")
            ui.button(
                "Abrir pasta output",
                icon="folder_open",
                on_click=lambda p=result.output_dir: _open_output_dir(p),
            ).props("flat dense no-caps color=primary")

            with ui.element("div").classes("geo-batch-result-list w-full mt-4"):
                for row in result.rows:
                    if row.success:
                        ui.html(
                            "<div class='geo-batch-result-row geo-batch-result-row--ok'>"
                            f"<span>#{row.row_num}</span> {row.topic[:50]}"
                            f"<code class='geo-meta-caption'>{Path(row.md_path).name}</code>"
                            f" · {row.word_count or 0:,} palavras"
                            "</div>"
                        )
                    else:
                        ui.html(
                            "<div class='geo-batch-result-row geo-batch-result-row--err'>"
                            f"<span>#{row.row_num}</span> {row.topic[:50]}"
                            f" — {row.error or 'erro'}"
                            "</div>"
                        )

    def _reset_batch_progress_ui() -> None:
        bar = w.get("progress_bar")
        label = w.get("progress_label")
        btn = w.get("run_btn")
        if bar:
            bar.visible = False
        if label:
            label.visible = False
        if btn:
            btn.enable()

    async def on_start_batch() -> None:
        alert_box.clear()
        result_box.clear()
        specs = state["specs"]
        if not specs:
            with alert_box:
                ui.label("Envie um CSV com pelo menos uma linha válida.").classes(
                    ALERT_WARNING
                )
            return

        btn = w.get("run_btn")
        bar = w.get("progress_bar")
        label = w.get("progress_label")
        if btn:
            btn.disable()

        provider_val = w["provider_select"].value
        provider = None if provider_val == "auto" else provider_val
        use_llm = bool(w["use_llm"].value)
        provider_resolved = provider or config.provider
        notify_webhook = bool(w.get("notify_webhook") and w["notify_webhook"].value)
        try:
            owner_id = require_session_user_id()
        except RuntimeError:
            owner_id = None
        save_to_history = bool(
            w.get("save_history") and w["save_history"].value and owner_id
        )
        if w.get("save_history") and w["save_history"].value and not owner_id:
            with alert_box:
                ui.label("Faça login para guardar o lote no histórico.").classes(
                    ALERT_WARNING
                )

        def _on_batch_failed(err: str) -> None:
            with alert_box:
                ui.label(f"Erro no lote: {err}").classes(ALERT_ERROR)
            _reset_batch_progress_ui()

        if should_queue_batch(len(specs), specs):
            with result_box:
                tracker_host = ui.column().classes("w-full")
            job_id = get_background_job_service().submit(
                lambda report: run_batch_job(
                    report,
                    specs=specs,
                    config=config,
                    use_llm=use_llm,
                    provider=provider_resolved,
                    user_id=owner_id,
                    save_to_history=save_to_history,
                    notify_webhook=notify_webhook,
                ),
                label=f"Lote CSV ({len(specs)} linha(s))",
                kind=JobKind.BATCH,
            )

            def _on_batch_done(result) -> None:
                try:
                    _render_batch_result(result)
                    if save_to_history and result.succeeded:
                        ui.notify(
                            f"{result.succeeded} matéria(s) guardada(s) no histórico.",
                            type="positive",
                        )
                    if notify_webhook:
                        ui.notify(
                            "Webhook de lote enviado (se configurado).",
                            type="info",
                        )
                finally:
                    _reset_batch_progress_ui()

            mount_background_job_tracker(
                job_id,
                host=tracker_host,
                on_completed=_on_batch_done,
                on_failed=_on_batch_failed,
            )
            return

        if bar:
            bar.visible = True
            bar.value = 0
        if label:
            label.visible = True

        def on_progress(current: int, total: int, topic: str) -> None:
            if bar:
                bar.value = current / total if total else 0
            if label:
                label.text = f"[{current}/{total}] {topic[:60]}…"

        try:
            result = await run.io_bound(
                run_batch,
                specs,
                use_llm=use_llm,
                use_advanced=config.use_advanced,
                provider=provider_resolved,
                manager=config.ai_manager if use_llm else None,
                on_progress=on_progress,
                user_id=owner_id,
                save_to_history=save_to_history,
            )
            if notify_webhook:
                await notify_batch_completed(
                    output_dir=result.output_dir,
                    total=result.total,
                    succeeded=result.succeeded,
                    failed=result.failed,
                )
            _render_batch_result(result)
            if save_to_history:
                ui.notify(
                    f"{result.succeeded} matéria(s) guardada(s) no histórico.",
                    type="positive",
                )
        except Exception as exc:
            logger.exception("Lote falhou: %s", exc)
            _on_batch_failed(str(exc))
        finally:
            _reset_batch_progress_ui()

    def _open_output_dir(path: str) -> None:
        folder = Path(path)
        if not folder.is_dir():
            folder = OUTPUT_DIR
        ui.notify(f"Ficheiros em: {folder.resolve()}", type="info")

    def _download_template() -> None:
        content = (
            _TEMPLATE_PATH.read_text(encoding="utf-8")
            if _TEMPLATE_PATH.is_file()
            else CSV_TEMPLATE
        )
        ui.download(content, "batch_template.csv")

    with ui.element("div").classes("geo-batch-page w-full"):
        page_header(
            "Lote CSV",
            "Importe uma planilha e gere dezenas de matérias GEO em Markdown, "
            "prontas para publicação ou revisão editorial.",
            eyebrow="Produção em escala",
        )

        with ui.element("div").classes("geo-batch-grid w-full"):
            with ui.element("div").classes("geo-batch-main"):
                with ui.element("section").classes("geo-urls-panel w-full"):
                    ui.label("Opções do lote").classes("geo-section-title mb-3")
                    with ui.element("div").classes("geo-batch-options-grid"):
                        w["use_llm"] = ui.switch("Usar IA na geração", value=True).props(
                            "dense color=primary"
                        )
                        w["save_history"] = ui.switch(
                            "Guardar cada matéria no histórico",
                            value=False,
                        ).props("dense")
                        w["notify_webhook"] = ui.switch(
                            "Notificar webhook ao concluir",
                            value=False,
                        ).props("dense")
                        if not load_production_settings().webhook_url:
                            w["notify_webhook"].disable()
                            w["notify_webhook"].tooltip(
                                "Configure GEO_WEBHOOK_URL no Dashboard"
                            )
                        w["provider_select"] = (
                            ui.select(
                                provider_options,
                                value="auto",
                                label="Provedor",
                            )
                            .classes("w-full geo-blog-input")
                            .props("outlined dense")
                        )
                        w["default_wc"] = (
                            ui.number(
                                label="Palavras (omissão)",
                                value=BLOG_WORD_COUNT_DEFAULT,
                                min=500,
                                max=6000,
                                step=100,
                            )
                            .classes("w-full geo-blog-input")
                            .props("outlined dense")
                        )
                        w["default_niche"] = (
                            ui.select(
                                niche_options,
                                value=niche_labels[0],
                                label="Nicho GEO",
                            )
                            .classes("w-full geo-blog-input")
                            .props("outlined dense")
                        )

                    if not config.ready_providers:
                        ui.label(
                            "Nenhum provedor de IA configurado — o lote usará modo local "
                            "se desativar a IA."
                        ).classes("geo-meta-caption mb-3")

                with ui.element("section").classes("geo-urls-panel w-full mt-4"):
                    with ui.row().classes(
                        "w-full items-center justify-between flex-wrap gap-2 mb-4"
                    ):
                        ui.label("Planilha CSV").classes("geo-section-title")
                        with ui.row().classes("gap-2"):
                            ui.button(
                                "Modelo CSV",
                                icon="download",
                                on_click=_download_template,
                            ).props("flat dense no-caps color=primary")
                            ui.button(
                                "Limpar",
                                icon="delete",
                                on_click=clear_upload,
                            ).props("flat dense no-caps")

                    ui.upload(
                        on_upload=on_csv_upload,
                        auto_upload=True,
                        max_files=1,
                    ).props(
                        'accept=".csv,text/csv" '
                        'label="Arraste o CSV ou clique para enviar"'
                    ).classes("w-full geo-batch-upload")

                    ui.label("Pré-visualização").classes("geo-blog-field-label mt-4")
                    preview_box

                with ui.element("section").classes("geo-urls-panel w-full mt-4"):
                    w["progress_label"] = ui.label("").classes("geo-meta-caption")
                    w["progress_bar"] = ui.linear_progress(
                        value=0, show_value=False
                    ).classes("w-full")
                    w["progress_label"].visible = False
                    w["progress_bar"].visible = False

                    w["run_btn"] = (
                        ui.button(
                            "Gerar lote",
                            icon="play_arrow",
                            on_click=lambda: asyncio.create_task(on_start_batch()),
                        )
                        .props("no-caps unelevated")
                        .classes("geo-urls-process-btn")
                    )

            with ui.element("aside").classes("geo-batch-side"):
                with ui.element("section").classes("geo-urls-panel w-full"):
                    ui.label("Colunas do CSV").classes("geo-section-title mb-3")
                    for col in (
                        "tema *",
                        "urls",
                        "palavras_chave",
                        "publico",
                        "tom",
                        "palavras",
                        "marca",
                        "cta",
                        "faq",
                        "angulo",
                        "nicho",
                        "slug",
                    ):
                        with ui.element("div").classes("geo-tip-item mb-1"):
                            ui.icon("table_rows", size="sm").classes("text-primary")
                            ui.label(col).classes("text-body2")

                with ui.element("section").classes("geo-urls-panel w-full mt-4"):
                    ui.label("Dicas").classes(
                        "text-primary text-xs font-semibold uppercase tracking-widest mb-3"
                    )
                    with ui.element("ul").classes("geo-tip-list"):
                        for tip in _BATCH_TIPS:
                            with ui.element("li").classes("geo-tip-item"):
                                with ui.element("div").classes("geo-tip-item__icon"):
                                    ui.icon("check", size="sm")
                                ui.html(f"<p>{tip}</p>")

        result_box

    render_preview()
