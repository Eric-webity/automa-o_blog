"""Aba: métricas e estado de produção."""

from __future__ import annotations

import asyncio

from nicegui import run, ui

from config.production import load_production_settings
from services.analytics import check_api_health, get_dashboard_stats
from ui.components.webhook_panel import build_webhook_panel
from ui.widgets import page_header

_PROVIDER_LABELS = {
    "openai": "OpenAI",
    "anthropic": "Anthropic",
    "openrouter": "OpenRouter",
    "ollama": "Ollama",
    "lmstudio": "LM Studio",
}

_API_ROUTES = [
    ("GET", "/api/health", "Público"),
    ("GET", "/api/v1/stats", "Métricas"),
    ("GET", "/api/v1/articles", "Listar"),
    ("GET", "/api/v1/articles/{id}", "Detalhe"),
    ("POST", "/api/v1/articles/generate", "Gerar"),
    ("POST", "/api/v1/articles/publish", "CMS externo"),
    ("DELETE", "/api/v1/articles/{id}", "Excluir"),
]


def _provider_label(name: str) -> str:
    return _PROVIDER_LABELS.get(name, name)


def _status_badge(ok: bool, ok_text: str, fail_text: str) -> None:
    css = "geo-status-badge geo-status-badge--ok" if ok else "geo-status-badge geo-status-badge--warn"
    ui.html(f'<span class="{css}">{ok_text if ok else fail_text}</span>')


def build_tab_dashboard(config) -> None:
    """Dashboard operacional do Content Studio."""
    page_header(
        "Dashboard",
        "Visão geral, integrações e atalhos para o histórico.",
    )

    settings = load_production_settings()
    stats_container = ui.row().classes("w-full gap-4 flex-wrap")
    providers_container = ui.row().classes("w-full gap-2 flex-wrap mt-2")
    recent_container = ui.column().classes("w-full gap-2 mt-4")
    ops_container = ui.column().classes("w-full gap-2 mt-4")
    api_container = ui.column().classes("w-full gap-2 mt-4")
    webhook_container = ui.column().classes("w-full gap-2 mt-4 geo-webhook-panel")

    def render_stats(data: dict, health: dict) -> None:
        stats_container.clear()
        with stats_container:
            for label, value, icon in (
                ("Matérias", data["total_articles"], "article"),
                ("Últimos 7 dias", data["articles_last_7_days"], "calendar_today"),
                ("Com IA", data["llm_articles"], "smart_toy"),
                ("Modo local", data["local_articles"], "edit_note"),
                ("Média palavras", data["avg_word_count"], "text_fields"),
            ):
                with ui.card().classes("geo-stat-card"):
                    ui.icon(icon).classes("text-primary text-h5")
                    ui.label(str(value)).classes("text-h5 font-bold")
                    ui.label(label).classes("text-caption text-grey-7")

        providers_container.clear()
        with providers_container:
            ui.label("Provedores de IA prontos").classes("text-subtitle2 w-full")
            ready = data.get("ready_providers") or []
            if ready:
                for name in ready:
                    ui.html(
                        f'<span class="geo-chip geo-chip--primary">{_provider_label(name)}</span>'
                    )
            else:
                ui.label("Nenhum provedor configurado.").classes("text-grey-7")
                ui.button(
                    "Configurar IA",
                    on_click=lambda: setattr(config._tabs, "value", config._tab_settings)
                    if getattr(config, "_tab_settings", None)
                    else None,
                ).props("flat dense color=primary")

        recent_container.clear()
        with recent_container:
            with ui.row().classes("w-full items-center justify-between"):
                ui.label("Últimas matérias").classes("text-subtitle2")
                ui.button(
                    "Ver histórico",
                    icon="history",
                    on_click=config.go_history_tab,
                ).props("flat dense color=primary")

            recent = data.get("recent_articles") or []
            if not recent:
                ui.label("Nenhuma matéria salva ainda.").classes("text-grey-7")
            else:
                for item in recent:
                    with ui.row().classes("geo-recent-row w-full items-center"):
                        with ui.column().classes("gap-0 flex-grow"):
                            ui.label(item["title"]).classes("text-body2 font-medium")
                            ui.label(
                                f"#{item['id']} · {item['status']} · {item['created_at']} · "
                                f"{item['word_count']} palavras"
                            ).classes("text-caption text-grey-7")
                        ui.button(
                            icon="open_in_new",
                            on_click=lambda i=item["id"]: config.open_article_in_history(i),
                        ).props("flat round dense color=primary")

        ops_container.clear()
        with ops_container:
            ui.label("Operação e armazenamento").classes("text-subtitle2")
            by_status = data.get("by_status") or {}
            if by_status:
                parts = [f"{name}: {count}" for name, count in sorted(by_status.items())]
                ui.label(" · ".join(parts)).classes("text-body2")
            ui.label(
                f"Base de dados: {data.get('storage_db_label', '0 B')} · "
                f"Exportações (output/): {data.get('storage_output_label', '0 B')}"
            ).classes("text-caption text-grey-7")

            ui.separator().classes("my-2")
            ui.label("Produção").classes("text-subtitle2")
            with ui.row().classes("gap-2 flex-wrap items-center"):
                ui.label(f"Ambiente: {settings.env}").classes("text-body2")
                _status_badge(
                    settings.api_enabled,
                    "API ativa",
                    "API desativada",
                )
                _status_badge(
                    data.get("api_key_configured", False),
                    "Chave API definida",
                    "Sem chave API",
                )
                _status_badge(
                    data.get("webhook_configured", False),
                    "Webhook OK",
                    "Webhook ausente",
                )
                _status_badge(
                    data.get("cms_configured", False),
                    "CMS externo OK",
                    "CMS não configurado",
                )

        api_container.clear()
        with api_container:
            ui.label("API REST").classes("text-subtitle2")
            with ui.row().classes("gap-2 items-center flex-wrap"):
                api_ok = health.get("ok", False)
                _status_badge(api_ok, f"Health OK · v{health.get('version', '?')}", "Health falhou")
                if health.get("require_api_key"):
                    ui.label("Autenticação obrigatória nas rotas /api/v1/*").classes(
                        "text-caption text-grey-7"
                    )

            with ui.column().classes("w-full gap-1 mt-2"):
                for method, path, desc in _API_ROUTES:
                    ui.label(f"{method} {path} — {desc}").classes(
                        "text-caption text-grey-8 font-mono"
                    )

    async def refresh() -> None:
        try:
            data = await run.io_bound(get_dashboard_stats)
            health = await run.io_bound(check_api_health)
            render_stats(data, health)
        except RuntimeError:
            # A aba pode ser desmontada durante troca rápida de navegação.
            return

    webhook_container.clear()
    with webhook_container:
        build_webhook_panel()

    with ui.row().classes("gap-2 mb-2"):
        ui.button("Atualizar", icon="refresh", on_click=refresh).props("outline")
        ui.button("Criar matéria", icon="edit_note", on_click=lambda: setattr(
            config._tabs, "value", config._tab_blog
        ) if config._tab_blog else None).props("outline")

    asyncio.create_task(refresh())
