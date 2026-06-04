"""Painel de acompanhamento de trabalhos em fila (segundo plano)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from nicegui import ui

from services.background_jobs import BackgroundJob, JobStatus, get_background_job_service


def render_queue_notice() -> None:
    """Aviso de que o trabalho corre em fila e a UI permanece livre."""
    with ui.element("div").classes("geo-queue-notice w-full"):
        with ui.row().classes("items-start gap-2"):
            ui.icon("schedule", size="sm").classes("text-primary mt-0.5")
            ui.label(
                "Tarefa longa em fila de segundo plano — pode navegar noutras páginas. "
                "O progresso atualiza aqui automaticamente."
            ).classes("geo-meta-caption")


def mount_background_job_tracker(
    job_id: str,
    *,
    host: ui.element,
    on_completed: Callable[[Any], None],
    on_failed: Callable[[str], None],
    poll_seconds: float = 0.45,
) -> None:
    """
    Mostra barra de progresso e faz polling até o trabalho terminar.

    ``on_completed`` / ``on_failed`` são chamados no loop principal da UI.
    """
    host.clear()
    with host:
        render_queue_notice()
        status_label = ui.label("Na fila…").classes("geo-queue-status w-full")
        progress_bar = ui.linear_progress(value=0, show_value=False).classes(
            "w-full geo-queue-progress"
        )

    def _apply_job(job: BackgroundJob) -> None:
        progress_bar.value = job.progress
        text = job.message or job.label
        status_label.text = f"{text} ({int(job.progress * 100)}%)"

    def _poll() -> None:
        job = get_background_job_service().get(job_id)
        if not job:
            poll_timer.deactivate()
            on_failed("Trabalho não encontrado.")
            return
        _apply_job(job)
        if job.status == JobStatus.COMPLETED:
            poll_timer.deactivate()
            ui.notify(f"Concluído: {job.label}", type="positive")
            on_completed(job.result)
        elif job.status == JobStatus.FAILED:
            poll_timer.deactivate()
            ui.notify(f"Falhou: {job.label}", type="negative")
            on_failed(job.error or "Erro desconhecido")

    poll_timer = ui.timer(poll_seconds, _poll, active=True)
    _poll()


def mount_global_job_indicator() -> None:
    """Indicador compacto na sidebar (trabalhos activos)."""
    indicator = ui.label("").classes("geo-queue-global-indicator")

    def _refresh() -> None:
        n = get_background_job_service().active_count()
        if n:
            indicator.text = f"{n} tarefa(s) em segundo plano"
            indicator.visible = True
        else:
            indicator.visible = False

    ui.timer(1.0, _refresh, active=True)
    _refresh()
