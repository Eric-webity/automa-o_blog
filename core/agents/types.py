"""Tipos do pipeline multi-agente (progresso na UI)."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum


class AgentStage(StrEnum):
    """Etapas visíveis na UI durante a geração."""

    RESEARCHER = "researcher"
    WRITER = "writer"
    EDITOR = "editor"
    DONE = "done"
    FAILED = "failed"


@dataclass
class AgentProgress:
    """Evento de progresso emitido para a interface."""

    stage: AgentStage
    message: str
    attempt: int = 1
    max_attempts: int = 1
    progress: float = 0.0


ProgressCallback = Callable[[AgentProgress], None]
