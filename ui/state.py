"""Estado partilhado da UI NiceGUI."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from dotenv import load_dotenv

from services.ai_manager import AIManager


@dataclass
class AppConfig:
    use_advanced: bool = True
    use_llm: bool = True
    provider: str | None = None
    ai_manager: AIManager | None = None
    enabled_providers: list[str] = field(default_factory=list)
    ready_providers: list[str] = field(default_factory=list)
    _tabs: Any = field(default=None, repr=False)
    _tab_history: Any = field(default=None, repr=False)
    open_history_article: Callable[[int], None] | None = field(
        default=None, repr=False
    )

    def go_history_tab(self) -> None:
        """Muda para a aba Histórico."""
        if self._tabs is not None and self._tab_history is not None:
            self._tabs.value = self._tab_history

    def open_article_in_history(self, article_id: int) -> None:
        """Abre matéria no histórico e muda de aba."""
        self.go_history_tab()
        if self.open_history_article:
            self.open_history_article(article_id)


def create_app_config() -> AppConfig:
    load_dotenv()
    try:
        mgr = AIManager()
        return AppConfig(
            ai_manager=mgr,
            enabled_providers=mgr.list_enabled_providers(),
            ready_providers=mgr.list_ready_providers(),
        )
    except Exception:
        return AppConfig(enabled_providers=[], ready_providers=[])


def refresh_ai_manager(config: AppConfig) -> None:
    """Recarrega .env e YAML após alterações na aba de configuração."""
    load_dotenv(override=True)
    try:
        config.ai_manager = AIManager()
        config.enabled_providers = config.ai_manager.list_enabled_providers()
        config.ready_providers = config.ai_manager.list_ready_providers()
    except Exception:
        config.ai_manager = None
        config.enabled_providers = []
        config.ready_providers = []
