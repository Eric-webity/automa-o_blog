"""Indicadores visuais do pipeline multi-agente."""

from __future__ import annotations

from nicegui import ui

from core.agents.types import AgentProgress, AgentStage, ProgressCallback

_AGENT_LABELS: dict[AgentStage, str] = {
    AgentStage.RESEARCHER: "Pesquisador",
    AgentStage.WRITER: "Redator",
    AgentStage.EDITOR: "Editor",
    AgentStage.DONE: "Concluído",
    AgentStage.FAILED: "Falhou",
}


class AgentProgressPanel:
    """Barra de progresso e chips por agente ativo."""

    def __init__(self) -> None:
        self._stage_labels: dict[AgentStage, ui.label] = {}
        self._progress_bar = ui.linear_progress(value=0, show_value=False).classes(
            "w-full geo-progress-bar"
        )
        self._status_label = ui.label("A iniciar pipeline…").classes("geo-loading-text")

        with ui.row().classes("w-full gap-2 mt-3 flex-wrap"):
            for stage in (AgentStage.RESEARCHER, AgentStage.WRITER, AgentStage.EDITOR):
                chip = ui.label(_AGENT_LABELS[stage]).classes("geo-agent-chip")
                self._stage_labels[stage] = chip

    def reset(self) -> None:
        """Reinicia indicadores antes de nova geração."""
        self._progress_bar.set_value(0)
        self._status_label.set_text("A iniciar pipeline…")
        for stage, chip in self._stage_labels.items():
            chip.set_text(_AGENT_LABELS[stage])
            chip.classes(remove="geo-agent-chip--active geo-agent-chip--done geo-agent-chip--error")

    def _highlight_stage(self, active: AgentStage) -> None:
        """Destaca o agente ativo nos chips."""
        for stage, chip in self._stage_labels.items():
            chip.classes(remove="geo-agent-chip--active geo-agent-chip--done")
            if stage == active:
                chip.classes(add="geo-agent-chip--active")

    def build_callback(self) -> ProgressCallback:
        """Retorna callback compatível com o orquestrador assíncrono."""

        def on_progress(event: AgentProgress) -> None:
            value = max(0.0, min(1.0, event.progress))
            if event.stage == AgentStage.DONE:
                value = 1.0
            self._progress_bar.set_value(value)
            agent_name = _AGENT_LABELS.get(event.stage, event.stage.value)
            self._status_label.set_text(f"{agent_name}: {event.message}")

            if event.stage in self._stage_labels:
                self._highlight_stage(event.stage)
            if event.stage == AgentStage.DONE:
                for chip in self._stage_labels.values():
                    chip.classes(remove="geo-agent-chip--active", add="geo-agent-chip--done")
            if event.stage == AgentStage.FAILED:
                for chip in self._stage_labels.values():
                    chip.classes(remove="geo-agent-chip--active", add="geo-agent-chip--error")

        return on_progress
