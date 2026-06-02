"""Aba: Settings & API — provedores de IA, chaves REST e integrações."""

from __future__ import annotations

import asyncio
import json

from nicegui import run, ui

from config.production import load_production_settings
from config.settings_store import (
    mask_key,
    normalize_lmstudio_url,
    read_env_keys,
    read_integration_env,
    read_lmstudio_model,
    read_lmstudio_url,
    read_ollama_url,
    read_provider_flags,
    write_env_keys,
    write_integration_env,
    write_lmstudio_settings,
    write_ollama_url,
    write_provider_flags,
)
from services.analytics import check_api_health, get_dashboard_stats
from services.url_cache import (
    cache_file_count,
    cache_ttl_hours,
    clear_url_cache,
    is_cache_enabled,
)
from ui.constants import (
    ALERT_SUCCESS,
    ALERT_WARNING,
    PROVIDER_DESCRIPTIONS,
    PROVIDER_ICONS,
    PROVIDER_ORDER,
    PROVIDER_SETTINGS_LABELS,
    provider_label,
)
from ui.pages.routes import ROUTE_DASHBOARD
from ui.state import refresh_ai_manager


def _section_header(title: str, description: str) -> None:
    with ui.element("div").classes("geo-section-header"):
        ui.label(title).classes("geo-section-title")
        ui.label(description).classes("geo-section-desc")


def _display_api_key(raw: str) -> str:
    masked = mask_key(raw)
    if not masked:
        return "sk-geo-************"
    suffix = masked[-4:] if len(masked) >= 4 else "****"
    return f"sk-geo-**********{suffix}"


def build_tab_settings(config) -> None:
    from ui.widgets import page_header

    with ui.element("div").classes("geo-settings-page w-full"):
        page_header(
            "Settings & API",
            "Gerencie provedores de IA, chaves de API e integrações do workspace.",
            eyebrow="Workspace",
        )

        status_box = ui.column().classes("w-full")
        main_form_box = ui.column().classes("geo-settings-main w-full")
        sidebar_box = ui.column().classes("geo-settings-side w-full")
        footer_box = ui.row().classes("geo-settings-footer w-full")

        flags_state: dict[str, bool] = {}
        inputs: dict[str, ui.input] = {}
        ollama_input: ui.input | None = None
        lmstudio_input: ui.input | None = None
        lmstudio_model_input: ui.input | None = None
        geo_api_input: ui.input | None = None
        test_select: ui.select | None = None
        test_result: ui.label | None = None
        compare_box: ui.column | None = None
        provider_cards_host: ui.element | None = None

        saved_snapshot: dict = {}

        def render_status() -> None:
            status_box.clear()
            ready = config.ready_providers or []
            enabled = config.enabled_providers or []
            with status_box:
                if ready:
                    labels = ", ".join(provider_label(p) for p in ready)
                    ui.html(
                        f'<div class="{ALERT_SUCCESS}">'
                        f"Prontos para uso: {labels}</div>"
                    )
                elif enabled:
                    ui.html(
                        f'<div class="{ALERT_WARNING}">'
                        "Provedores habilitados, mas sem credenciais válidas. "
                        "Configure as chaves abaixo.</div>"
                    )
                else:
                    ui.html(
                        f'<div class="{ALERT_WARNING}">'
                        "Nenhum provedor habilitado.</div>"
                    )

        def render_provider_cards() -> None:
            if provider_cards_host is None:
                return
            provider_cards_host.clear()
            with provider_cards_host:
                with ui.element("div").classes("geo-provider-grid"):
                    for name in PROVIDER_ORDER:
                        active = flags_state.get(name, False)
                        card_cls = (
                            "geo-provider-card geo-provider-card--active"
                            if active
                            else "geo-provider-card"
                        )

                        def toggle_provider(_e, n=name) -> None:
                            flags_state[n] = not flags_state.get(n, False)
                            render_provider_cards()

                        with ui.element("div").classes(card_cls).on("click", toggle_provider):
                            if active:
                                with ui.element("div").classes("geo-provider-card__check"):
                                    ui.element("div").classes("geo-provider-card__check-dot")
                            with ui.element("div").classes("geo-provider-card__icon"):
                                ui.icon(PROVIDER_ICONS.get(name, "smart_toy"))
                            ui.label(PROVIDER_SETTINGS_LABELS.get(name, name)).classes(
                                "geo-provider-card__name"
                            )
                            ui.label(PROVIDER_DESCRIPTIONS.get(name, "")).classes(
                                "geo-provider-card__desc"
                            )

        def _live_overrides(name: str) -> dict | None:
            ollama_url = saved_snapshot.get("ollama_url", read_ollama_url())
            lmstudio_url = saved_snapshot.get("lmstudio_url", read_lmstudio_url())
            lmstudio_model = saved_snapshot.get("lmstudio_model", read_lmstudio_model())
            if name == "lmstudio" and lmstudio_input:
                return {
                    "base_url": normalize_lmstudio_url(lmstudio_input.value or lmstudio_url),
                    "models": {
                        "rewrite": (lmstudio_model_input.value or lmstudio_model).strip(),
                        "blog_long": (lmstudio_model_input.value or lmstudio_model).strip(),
                    },
                }
            if name == "ollama" and ollama_input:
                return {
                    "base_url": (ollama_input.value or ollama_url).strip(),
                    "models": {"rewrite": "llama3", "blog_long": "llama3"},
                }
            return None

        async def compare_config() -> None:
            if compare_box is None or test_select is None:
                return
            compare_box.clear()
            name = test_select.value
            mgr = config.ai_manager
            if not mgr:
                return
            overrides = _live_overrides(name)
            report = await run.io_bound(mgr.diagnose_provider, name, overrides)
            with compare_box:
                ui.label("Comparação — formulário vs servidor").classes("text-subtitle2")
                for chk in report.get("checks", []):
                    icon = "✓" if chk["ok"] else "✗"
                    color = "text-positive" if chk["ok"] else "text-negative"
                    ui.label(f"{icon} {chk['label']}").classes(f"text-body2 {color}")
                    ui.label(f"  Configurado: {chk['expected']}").classes("text-caption")
                    ui.label(f"  Servidor: {chk['actual']}").classes("text-caption")
                    if chk.get("hint"):
                        ui.label(f"  → {chk['hint']}").classes("text-caption text-orange-800")

        async def test_connection() -> None:
            if test_result is None or test_select is None or compare_box is None:
                return
            test_result.text = "A testar..."
            compare_box.clear()
            name = test_select.value
            mgr = config.ai_manager
            if not mgr:
                test_result.text = "Salve a configuração antes de testar."
                test_result.classes(replace="text-negative text-caption")
                return
            overrides = _live_overrides(name)
            ok, msg = await run.io_bound(mgr.test_provider, name, overrides)
            test_result.text = msg
            test_result.classes(
                replace="text-positive text-caption" if ok else "text-negative text-caption"
            )
            await compare_config()

        async def save_settings() -> None:
            nonlocal saved_snapshot
            updates = {}
            for env_name, inp in inputs.items():
                val = (inp.value or "").strip()
                if val:
                    updates[env_name] = val
            if updates:
                write_env_keys(updates)
            write_provider_flags(dict(flags_state))
            if ollama_input:
                write_ollama_url(
                    (ollama_input.value or "").strip() or "http://localhost:11434"
                )
            if lmstudio_input and lmstudio_model_input:
                write_lmstudio_settings(
                    lmstudio_input.value or saved_snapshot.get("lmstudio_url", read_lmstudio_url()),
                    (lmstudio_model_input.value or "").strip() or "local-model",
                )
            if geo_api_input:
                api_val = (geo_api_input.value or "").strip()
                if api_val:
                    write_integration_env({"GEO_API_KEY": api_val})
            refresh_ai_manager(config)
            render_status()
            ui.notify("Configuração salva.", type="positive")
            build_form()

        def copy_api_key() -> None:
            key = saved_snapshot.get("geo_api_key", "")
            if not key:
                ui.notify("Nenhuma chave API configurada.", type="warning")
                return
            ui.run_javascript(f"navigator.clipboard.writeText({json.dumps(key)})")
            ui.notify("Chave copiada.", type="positive")

        async def load_usage_panel() -> None:
            try:
                data = await run.io_bound(get_dashboard_stats)
                health = await run.io_bound(check_api_health)
            except RuntimeError:
                return
            sidebar_box.clear()
            with sidebar_box:
                settings = load_production_settings()
                with ui.element("section").classes("geo-glass-card geo-glass-card--accent w-full"):
                    with ui.row().classes("w-full items-start justify-between mb-4"):
                        ui.label("Uso do workspace").classes("geo-section-title")
                        pill = "geo-status-pill--ok" if health.get("ok") else "geo-status-pill--warn"
                        ui.html(
                            f'<span class="geo-status-pill {pill}">'
                            f'{"Ativo" if health.get("ok") else "Atenção"}</span>'
                        )

                    total = data.get("total_articles", 0)
                    llm = data.get("llm_articles", 0)
                    pct = min(100, int((llm / total * 100) if total else 0))

                    with ui.column().classes("w-full gap-3 mb-4"):
                        with ui.element("div").classes("geo-usage-stat-row"):
                            ui.label("Matérias geradas")
                            ui.html(f"<strong>{total}</strong>")
                        with ui.element("div").classes("geo-usage-stat-row"):
                            ui.label("Com IA")
                            ui.html(f"<strong>{llm}</strong>")
                        with ui.element("div").classes("geo-usage-bar"):
                            ui.element("div").classes("geo-usage-bar__fill").style(
                                f"width: {pct}%"
                            )
                        with ui.element("div").classes("geo-usage-stat-row"):
                            ui.label("Base de dados")
                            ui.html(f"<strong>{data.get('storage_db_label', '0 B')}</strong>")
                        with ui.element("div").classes("geo-usage-stat-row"):
                            ui.label("Exportações")
                            ui.html(
                                f"<strong>{data.get('storage_output_label', '0 B')}</strong>"
                            )

                    ui.button(
                        "Ver dashboard",
                        on_click=lambda: ui.navigate.to(ROUTE_DASHBOARD),
                    ).props("outline dense").classes("w-full geo-btn-outline")

                with ui.element("section").classes("geo-glass-card w-full"):
                    ui.label("Integrações").classes("geo-section-title mb-3")
                    for label, ok in (
                        ("API REST", data.get("api_key_configured")),
                        ("Webhook", data.get("webhook_configured")),
                        ("CMS externo", data.get("cms_configured")),
                    ):
                        pill_cls = "geo-status-pill--ok" if ok else "geo-status-pill--warn"
                        text = "Configurado" if ok else "Pendente"
                        with ui.row().classes("w-full items-center justify-between py-1"):
                            ui.label(label).classes("text-body2")
                            ui.html(f'<span class="geo-status-pill {pill_cls}">{text}</span>')

                    if not settings.api_enabled:
                        ui.label("API desativada (GEO_API_ENABLED=false)").classes(
                            "text-caption text-orange-8 mt-2"
                        )

                    ready = data.get("ready_providers") or []
                    if ready:
                        ui.label("Provedores prontos").classes("text-caption text-grey-7 mt-3")
                        with ui.row().classes("gap-1 flex-wrap mt-1"):
                            for name in ready:
                                ui.html(
                                    f'<span class="geo-chip geo-chip--primary">{name}</span>'
                                )

                with ui.element("section").classes("geo-glass-card w-full"):
                    ui.label("Cache de URLs").classes("geo-section-title mb-2")
                    if is_cache_enabled():
                        ui.label(
                            f"TTL: {int(cache_ttl_hours())}h · "
                            f"{cache_file_count()} página(s) em cache"
                        ).classes("text-caption text-grey-7")
                        ui.label(
                            "URLs já buscadas são reutilizadas em novas matérias "
                            "(menos tempo e custo de rede)."
                        ).classes("text-caption text-grey-7 mt-1")
                    else:
                        ui.label("Desativado (GEO_URL_CACHE_TTL_HOURS=0).").classes(
                            ALERT_WARNING
                        )

                    async def clear_cache() -> None:
                        removed = await run.io_bound(clear_url_cache)
                        ui.notify(
                            f"Cache limpo ({removed} ficheiro(s) removidos).",
                            type="positive",
                        )
                        await load_usage_panel()

                    ui.button(
                        "Limpar cache de URLs",
                        on_click=lambda: asyncio.create_task(clear_cache()),
                    ).props("outline dense").classes("w-full mt-2")

        def build_form() -> None:
            nonlocal ollama_input, lmstudio_input, lmstudio_model_input
            nonlocal geo_api_input, test_select, test_result, compare_box
            nonlocal provider_cards_host, saved_snapshot

            env_keys = read_env_keys()
            integration = read_integration_env()
            flags_state.clear()
            flags_state.update(read_provider_flags())
            ollama_url = read_ollama_url()
            lmstudio_url = read_lmstudio_url()
            lmstudio_model = read_lmstudio_model()
            geo_api_key = integration.get("GEO_API_KEY", "")

            saved_snapshot = {
                "ollama_url": ollama_url,
                "lmstudio_url": lmstudio_url,
                "lmstudio_model": lmstudio_model,
                "geo_api_key": geo_api_key,
            }

            inputs.clear()
            main_form_box.clear()
            sidebar_box.clear()
            footer_box.clear()

            with ui.element("div").classes("geo-settings-grid w-full"):
                with main_form_box:
                    with ui.element("section").classes("geo-glass-card w-full"):
                        _section_header(
                            "Default AI Provider",
                            "Selecione os provedores ativos para extração e geração de conteúdo.",
                        )
                        provider_cards_host = ui.element("div").classes("w-full")
                        render_provider_cards()

                    with ui.element("section").classes("geo-glass-card w-full"):
                        with ui.row().classes("w-full items-start justify-between mb-4"):
                            _section_header(
                                "REST API Keys",
                                "Chave para autenticar chamadas à API REST (/api/v1/*).",
                            )
                        with ui.element("div").classes("geo-api-key-row w-full mb-4"):
                            with ui.row().classes("items-start gap-3 flex-grow"):
                                with ui.element("div").classes(
                                    "p-2 rounded-lg bg-primary/10 text-primary"
                                ):
                                    ui.icon("key")
                                with ui.column().classes("gap-1 flex-grow"):
                                    ui.label("Chave de produção").classes(
                                        "text-body2 font-medium"
                                    )
                                    with ui.row().classes("items-center gap-2"):
                                        ui.html(
                                            f'<code class="geo-api-key-code">'
                                            f"{_display_api_key(geo_api_key)}</code>"
                                        )
                                        ui.button(icon="content_copy", on_click=copy_api_key).props(
                                            "flat dense round color=primary"
                                        )
                                    pill = (
                                        "geo-status-pill--ok"
                                        if geo_api_key
                                        else "geo-status-pill--warn"
                                    )
                                    ui.html(
                                        f'<span class="geo-status-pill {pill}">'
                                        f'{"Active" if geo_api_key else "Não configurada"}</span>'
                                    )
                        geo_api_input = (
                            ui.input(
                                "Nova chave API (GEO_API_KEY)",
                                placeholder="Cole uma chave segura para substituir a atual",
                            )
                            .props("type=password outlined dense")
                            .classes("w-full")
                        )

                    with ui.element("section").classes("geo-glass-card w-full"):
                        _section_header(
                            "Chaves de provedores",
                            "Credenciais salvas no ficheiro .env.",
                        )
                        with ui.column().classes("w-full gap-2"):
                            for env_name, label in (
                                ("OPENAI_API_KEY", "OpenAI"),
                                ("ANTHROPIC_API_KEY", "Anthropic"),
                                ("OPENROUTER_API_KEY", "OpenRouter"),
                                ("LMSTUDIO_API_KEY", "LM Studio (opcional)"),
                            ):
                                masked = mask_key(env_keys.get(env_name, ""))
                                if env_name == "LMSTUDIO_API_KEY":
                                    hint = (
                                        f"Atual: {masked}"
                                        if masked
                                        else "Opcional — LM Studio aceita qualquer valor"
                                    )
                                else:
                                    hint = f"Atual: {masked}" if masked else "Não configurada"
                                inputs[env_name] = (
                                    ui.input(label, placeholder=hint)
                                    .props("type=password outlined dense")
                                    .classes("w-full")
                                )

                    with ui.element("section").classes("geo-glass-card w-full"):
                        _section_header(
                            "Servidores locais",
                            "URLs para Ollama e LM Studio.",
                        )
                        ollama_input = (
                            ui.input("Ollama — URL base", value=ollama_url)
                            .props("outlined dense")
                            .classes("w-full")
                        )
                        ui.label(
                            "Ollama usa porta 11434 — não confunda com LM Studio (1234)."
                        ).classes("text-caption text-grey-7")

                        lmstudio_input = (
                            ui.input("LM Studio — URL base", value=lmstudio_url)
                            .props("outlined dense")
                            .classes("w-full")
                        )
                        ui.label(
                            "No LM Studio: Developer → Local Server → Start Server (porta 1234)."
                        ).classes("text-caption text-grey-7")

                        lmstudio_model_input = (
                            ui.input(
                                "LM Studio — ID do modelo carregado",
                                value=lmstudio_model,
                            )
                            .props("outlined dense")
                            .classes("w-full")
                        )
                        ui.label(
                            "Identificador exibido no LM Studio ou em GET /v1/models."
                        ).classes("text-caption text-grey-7")

                    with ui.element("section").classes("geo-glass-card w-full"):
                        _section_header(
                            "Testar conexão",
                            "Valide credenciais e URLs antes de salvar.",
                        )
                        test_select = ui.select(
                            list(PROVIDER_ORDER),
                            label="Provedor",
                            value="openai",
                        ).classes("w-full")
                        test_result = ui.label("").classes("text-caption")
                        compare_box = ui.column().classes("w-full mt-2")
                        with ui.row().classes("gap-2 mt-2"):
                            ui.button("Testar", on_click=test_connection).props("outline")
                            ui.button("Comparar", on_click=compare_config).props("flat")

                with sidebar_box:
                    ui.spinner(size="md").classes("self-center geo-loading-spinner")
                    ui.label("A carregar estatísticas…").classes("geo-loading-text self-center")

            with footer_box:
                ui.button("Cancelar", on_click=build_form).classes("geo-btn-secondary")
                ui.button("Salvar alterações", on_click=save_settings).classes("geo-btn-primary")

            asyncio.create_task(load_usage_panel())

        render_status()
        build_form()
