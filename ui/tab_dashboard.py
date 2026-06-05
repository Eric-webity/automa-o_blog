"""Aba: dashboard operacional com layout Content Studio."""

from __future__ import annotations

import asyncio

from nicegui import run, ui

from config.production import load_production_settings
from services.analytics import check_api_health, get_dashboard_stats
from ui.auth import require_session_user_id
from ui.components.cms_panel import build_cms_panel
from ui.components.webhook_panel import build_webhook_panel
from services.ai_usage import format_cost_usd, format_tokens
from ui.constants import API_ROUTES, article_status_meta, provider_label
from ui.pages.routes import ROUTE_BLOG, ROUTE_SETTINGS
from ui.widgets import page_header


def _format_stat(value: int) -> str:
    if value >= 1_000_000:
        return f"{value / 1_000_000:.1f}M"
    if value >= 10_000:
        return f"{value / 1_000:.1f}k"
    return str(value)


def _progress_for_status(status: str) -> int:
    if status == "completed":
        return 100
    if status == "draft":
        return 45
    return 70


def _open_article(config, article_id: int) -> None:
    config.open_article_in_history(article_id)


def build_tab_dashboard(config) -> None:
    """Dashboard operacional do Content Studio."""
    settings = load_production_settings()
    stats_container = ui.element("div").classes("geo-dash-stats-grid w-full")
    projects_container = ui.element("div").classes("geo-dash-projects-grid w-full")
    integrations_container = ui.column().classes("w-full gap-4")
    ai_cost_container = ui.element("div").classes("geo-ai-cost-section w-full")

    def _header_actions() -> None:
        ui.button(
            "Atualizar",
            icon="refresh",
            on_click=lambda: asyncio.create_task(refresh()),
        ).props("flat dense no-caps color=primary")
        ui.button(
            "Ver histórico",
            icon="arrow_forward",
            on_click=config.go_history_tab,
        ).props("flat dense no-caps color=primary")

    with ui.element("div").classes("geo-dashboard-page w-full"):
        page_header(
            "Dashboard",
            "Métricas em tempo real do seu workspace.",
            eyebrow="Overview",
            actions=_header_actions,
        )
        with ui.element("section").classes("w-full"):
            stats_container

        with ui.element("section").classes("w-full"):
            with ui.element("div").classes("geo-dash-section-header"):
                with ui.column().classes("gap-0"):
                    ui.label("Matérias Recentes").classes("geo-section-title")
                    ui.label(
                        "Retome os seus fluxos de conteúdo mais recentes."
                    ).classes("geo-dash-section-desc")

            projects_container

        with ui.element("section").classes("w-full"):
            with ui.element("div").classes("geo-dash-section-header"):
                with ui.column().classes("gap-0"):
                    ui.label("Controle de gastos com IA").classes("geo-section-title")
                    ui.label(
                        "Tokens e custo estimado por provedor (últimos 30 dias)."
                    ).classes("geo-dash-section-desc")
            ai_cost_container

        with ui.element("section").classes("geo-dash-integrations w-full"):
            ui.label("Integrações e API").classes("geo-section-title")
            integrations_container

    def _render_stat_card(
        label: str,
        value: str,
        trend: str,
        icon: str,
        bg_icon: str,
        *,
        trend_muted: bool = False,
    ) -> None:
        trend_cls = (
            "geo-dash-stat-trend geo-dash-stat-trend--muted"
            if trend_muted
            else "geo-dash-stat-trend"
        )
        ui.html(
            f'<div class="geo-dash-stat-card">'
            f'<div class="geo-dash-stat-bg-icon"><span class="material-symbols-outlined" '
            f'style="font-size:5rem;color:var(--geo-primary)">{bg_icon}</span></div>'
            f'<p class="geo-dash-stat-label">'
            f'<span class="material-symbols-outlined text-primary" style="font-size:1rem">{icon}</span>'
            f"{label}</p>"
            f'<p class="geo-dash-stat-value">{value}</p>'
            f'<span class="{trend_cls}">{trend}</span>'
            f"</div>"
        )

    def _render_featured_project(item: dict) -> None:
        status_text, status_cls, status_icon = article_status_meta(item["status"])
        progress = _progress_for_status(item["status"])

        def open_item(_e, article_id=item["id"]) -> None:
            _open_article(config, article_id)

        with ui.element("div").classes(
            "geo-dash-project-card geo-dash-project-card--featured"
        ).on("click", open_item):
            with ui.element("div").classes("geo-dash-project-thumb"):
                ui.element("div").classes("geo-dash-project-thumb__overlay")
            with ui.element("div").classes("geo-dash-project-body"):
                with ui.column().classes("w-full"):
                    with ui.element("div").classes("geo-dash-project-top"):
                        ui.html(
                            f'<span class="geo-dash-status-pill {status_cls}">'
                            f'<span class="material-symbols-outlined" style="font-size:14px">'
                            f"{status_icon}</span>{status_text}</span>"
                        )
                        ui.html(
                            f'<span class="geo-dash-project-time">'
                            f'<span class="material-symbols-outlined" style="font-size:14px">'
                            f"schedule</span>{item['created_at']}</span>"
                        )
                    ui.label(item["title"]).classes("geo-dash-project-title")
                    ui.label(
                        f"Matéria #{item['id']} · {item['word_count']} palavras · "
                        f"status {item['status']}."
                    ).classes("geo-dash-project-desc")
                with ui.element("div").classes("geo-dash-project-footer"):
                    ui.label(f"{item['word_count']} palavras").classes(
                        "text-caption text-grey-7"
                    )
                    with ui.element("div").classes("geo-dash-progress-row"):
                        ui.label(f"{progress}%").classes("text-caption text-grey-7")
                        with ui.element("div").classes("geo-dash-progress-bar"):
                            ui.element("div").classes("geo-dash-progress-fill").style(
                                f"width: {progress}%"
                            )

    def _render_compact_project(item: dict) -> None:
        status_text, status_cls, status_icon = article_status_meta(item["status"])

        def open_item(_e, article_id=item["id"]) -> None:
            _open_article(config, article_id)

        with ui.element("div").classes(
            "geo-dash-project-card geo-dash-project-card--compact"
        ).on("click", open_item):
            with ui.element("div").classes("geo-dash-project-body"):
                with ui.column().classes("w-full"):
                    with ui.element("div").classes("geo-dash-project-top"):
                        ui.html(
                            f'<span class="geo-dash-status-pill {status_cls}">'
                            f'<span class="material-symbols-outlined" style="font-size:14px">'
                            f"{status_icon}</span>{status_text}</span>"
                        )
                    ui.label(item["title"]).classes("geo-dash-project-title")
                    ui.label(
                        f"{item['word_count']} palavras · criada em {item['created_at']}."
                    ).classes("geo-dash-project-desc")
                    with ui.element("div").classes("geo-dash-project-tags"):
                        ui.html(f'<span class="geo-dash-tag">#{item["id"]}</span>')
                        ui.html(f'<span class="geo-dash-tag">{item["status"]}</span>')
                with ui.element("div").classes("geo-dash-project-footer"):
                    ui.label(item["created_at"]).classes("text-caption text-grey-7")
                    ui.button(
                        icon="open_in_new",
                        on_click=lambda i=item["id"]: _open_article(config, i),
                    ).props("flat round dense color=primary")

    def _render_ai_cost_panel(ai_usage: dict) -> None:
        ai_cost_container.clear()
        week = ai_usage.get("last_7_days") or {}
        month = ai_usage.get("last_30_days") or {}
        today = ai_usage.get("today") or {}
        by_provider = ai_usage.get("by_provider_30d") or []
        recent = ai_usage.get("recent_calls") or []

        with ai_cost_container:
            with ui.element("div").classes("geo-ai-cost-grid"):
                for label, block, icon in (
                    ("Hoje", today, "today"),
                    ("7 dias", week, "date_range"),
                    ("30 dias", month, "calendar_month"),
                ):
                    with ui.element("div").classes("geo-ai-cost-card"):
                        with ui.row().classes("items-center gap-2 mb-2"):
                            ui.icon(icon, size="sm").classes("text-primary")
                            ui.label(label).classes("geo-ai-cost-card__label")
                        ui.label(format_cost_usd(block.get("cost_usd", 0))).classes(
                            "geo-ai-cost-card__value"
                        )
                        ui.label(
                            f"{format_tokens(block.get('total_tokens', 0))} tokens · "
                            f"{block.get('calls', 0)} chamada(s)"
                        ).classes("geo-meta-caption")

                if not ai_usage.get("has_data"):
                    with ui.element("div").classes("geo-ai-cost-empty"):
                        ui.icon("insights", size="md").classes("text-grey-6 mb-2")
                        ui.label(
                            "Ainda sem registos de IA. Gere matérias com IA ativa "
                            "para ver tokens e custo estimado aqui."
                        ).classes("geo-meta-caption")

            if by_provider:
                ui.label("Por provedor (30 dias)").classes(
                    "geo-section-title mt-4 mb-2"
                )
                max_cost = max((p.get("cost_usd") or 0) for p in by_provider) or 0.0001
                with ui.element("div").classes("geo-ai-cost-providers w-full"):
                    for row in by_provider:
                        pct = min(100, int((row.get("cost_usd") or 0) / max_cost * 100))
                        name = provider_label(row.get("provider", ""))
                        with ui.element("div").classes("geo-ai-cost-provider-row"):
                            with ui.row().classes(
                                "w-full items-center justify-between gap-2 mb-1"
                            ):
                                ui.label(name).classes("text-body2")
                                ui.label(
                                    format_cost_usd(row.get("cost_usd", 0))
                                ).classes("text-caption font-medium")
                            with ui.element("div").classes("geo-usage-bar"):
                                ui.element("div").classes("geo-usage-bar__fill").style(
                                    f"width: {pct}%"
                                )
                            ui.label(
                                f"{format_tokens(row.get('total_tokens', 0))} tokens · "
                                f"{row.get('calls', 0)} chamadas"
                            ).classes("geo-meta-caption")

            if recent:
                with ui.expansion(
                    "Chamadas recentes",
                    icon="receipt_long",
                    value=False,
                ).classes("w-full geo-ai-cost-recent mt-4"):
                    with ui.element("div").classes("geo-ai-cost-recent-table"):
                        for call in recent:
                            est = " ~" if call.get("estimated") else ""
                            ui.html(
                                "<div class='geo-ai-cost-recent-row'>"
                                f"<span class='geo-ai-cost-recent-time'>{call['created_at']}</span>"
                                f"<span class='geo-ai-cost-recent-main'>"
                                f"{provider_label(call['provider'])} · {call['task']}"
                                f" <em>({call['source']})</em></span>"
                                f"<span class='geo-ai-cost-recent-meta'>"
                                f"{format_tokens(call['total_tokens'])}{est} · "
                                f"{format_cost_usd(call['cost_usd'])}</span>"
                                "</div>"
                            )

            ui.label(
                "Custos em USD (estimativa com base em config/ai_pricing.yaml). "
                "Ollama/LM Studio aparecem como $0."
            ).classes("geo-meta-caption mt-3")

    def render_stats(data: dict, health: dict) -> None:
        stats_container.clear()
        projects_container.clear()
        integrations_container.clear()
        ai_cost_container.clear()

        week_count = data.get("articles_last_7_days", 0)
        total = data.get("total_articles", 0)
        llm = data.get("llm_articles", 0)
        ready_count = len(data.get("ready_providers") or [])

        with stats_container:
            _render_stat_card(
                "Total de matérias",
                _format_stat(total),
                (
                    f"+{week_count} nos últimos 7 dias"
                    if week_count
                    else "Sem novidades recentes"
                ),
                "analytics",
                "dataset",
                trend_muted=week_count == 0,
            )
            _render_stat_card(
                "Geradas com IA",
                _format_stat(llm),
                (
                    f"{ready_count} provedor(es) prontos"
                    if ready_count
                    else "Configure IA em Settings"
                ),
                "memory",
                "api",
                trend_muted=ready_count == 0,
            )
            _render_stat_card(
                "Média de palavras",
                _format_stat(data.get("avg_word_count", 0)),
                f"{data.get('local_articles', 0)} em modo local",
                "workspaces",
                "folder_special",
                trend_muted=True,
            )
            ai_week = (data.get("ai_usage") or {}).get("last_7_days") or {}
            _render_stat_card(
                "Custo IA (7 dias)",
                data.get("ai_cost_7d_label", "$0.00"),
                f"{data.get('ai_tokens_7d_label', '0')} tokens · "
                f"{ai_week.get('calls', 0)} chamada(s)",
                "payments",
                "savings",
                trend_muted=not (data.get("ai_usage") or {}).get("has_data"),
            )
        recent = data.get("recent_articles") or []
        with projects_container:
            if not recent:
                ui.label("Nenhuma matéria salva ainda.").classes("text-grey-7")
                with ui.element("div").classes(
                    "geo-dash-project-card geo-dash-project-card--compact"
                ):
                    with ui.element("div").classes("geo-dash-project-body"):
                        ui.label("Comece agora").classes("geo-dash-project-title")
                        ui.label(
                            "Crie a sua primeira matéria a partir de URLs ou texto manual."
                        ).classes("geo-dash-project-desc")
                        ui.button(
                            "Criar matéria",
                            icon="edit_note",
                            on_click=lambda: ui.navigate.to(ROUTE_BLOG),
                        ).props("color=primary").classes("mt-4 self-start")
            else:
                _render_featured_project(recent[0])
                for item in recent[1:3]:
                    _render_compact_project(item)

        _render_ai_cost_panel(data.get("ai_usage") or {})

        with integrations_container:
            ui.label("Estado de produção").classes("text-subtitle2")
            with ui.element("div").classes("geo-dash-badge-row"):
                badges = (
                    (settings.api_enabled, "API ativa", "API desativada"),
                    (data.get("api_key_configured"), "Chave API OK", "Sem chave API"),
                    (data.get("webhook_configured"), "Webhook OK", "Webhook ausente"),
                    (
                        data.get("cms_configured"),
                        "CMS externo OK",
                        "CMS não configurado",
                    ),
                )
                for ok, ok_text, fail_text in badges:
                    css = (
                        "geo-status-badge geo-status-badge--ok"
                        if ok
                        else "geo-status-badge geo-status-badge--warn"
                    )
                    ui.html(
                        f'<span class="{css}">{ok_text if ok else fail_text}</span>'
                    )

            ready = data.get("ready_providers") or []
            if ready:
                ui.label("Provedores prontos").classes("text-caption text-grey-7 mt-2")
                with ui.row().classes("gap-1 flex-wrap"):
                    for name in ready:
                        ui.html(
                            f'<span class="geo-chip geo-chip--primary">{provider_label(name)}</span>'
                        )
            else:
                ui.button(
                    "Configurar IA",
                    on_click=lambda: ui.navigate.to(ROUTE_SETTINGS),
                ).props("flat dense color=primary").classes("self-start")

            ui.separator().classes("my-2")
            api_ok = health.get("ok", False)
            api_label = (
                f"Health OK · v{health.get('version', '?')}"
                if api_ok
                else "Health falhou"
            )
            css = (
                "geo-status-badge geo-status-badge--ok"
                if api_ok
                else "geo-status-badge geo-status-badge--warn"
            )
            ui.html(f'<span class="{css}">{api_label}</span>')
            cache_line = ""
            if data.get("url_cache_enabled"):
                cache_line = (
                    f" · Cache URLs: {data.get('url_cache_entries', 0)} pág. "
                    f"(TTL {data.get('url_cache_ttl_hours', 24)}h)"
                )
            sim_pct = data.get("similarity_threshold_pct")
            sim_line = f" · Limiar similaridade: {sim_pct}%" if sim_pct else ""
            ui.label(
                f"Ambiente: {settings.env} · "
                f"Base: {data.get('storage_db_label', '0 B')} · "
                f"Exportações: {data.get('storage_output_label', '0 B')}"
                f"{cache_line}{sim_line}"
            ).classes("text-caption text-grey-7")

            with ui.expansion("Rotas da API REST", icon="api").classes("w-full"):
                for method, path, desc in API_ROUTES:
                    ui.html(
                        f'<div class="geo-dash-api-route">{method} {path} — {desc}</div>'
                    )

            with ui.expansion("Webhook (notificações)", icon="webhook").classes(
                "w-full"
            ):
                build_webhook_panel()

            with ui.expansion("CMS externo", icon="cloud_upload").classes("w-full"):
                build_cms_panel()

    async def refresh() -> None:
        try:
            owner_id = require_session_user_id()
            data = await run.io_bound(lambda: get_dashboard_stats(user_id=owner_id))
            health = await run.io_bound(check_api_health)
            render_stats(data, health)
        except RuntimeError:
            return

    asyncio.create_task(refresh())
