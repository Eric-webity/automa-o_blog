"""Estado partilhado da UI NiceGUI."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from dotenv import load_dotenv
from nicegui import ui

from services.ai_manager import AIManager
from ui.pages.routes import ROUTE_HISTORY


@dataclass
class AppConfig:
    use_advanced: bool = True
    use_llm: bool = True
    provider: str | None = None
    ai_manager: AIManager | None = None
    enabled_providers: list[str] = field(default_factory=list)
    ready_providers: list[str] = field(default_factory=list)
    open_history_article: Callable[[int], None] | None = field(default=None, repr=False)
    handle_logout: Callable[[], None] | None = field(default=None, repr=False)
    session_user_id: int | None = None

    def go_history_tab(self) -> None:
        """Navega para a página de Histórico."""
        ui.navigate.to(ROUTE_HISTORY)

    def open_article_in_history(self, article_id: int) -> None:
        """Abre uma matéria específica na página de Histórico."""
        ui.navigate.to(f"{ROUTE_HISTORY}?article={article_id}")


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
