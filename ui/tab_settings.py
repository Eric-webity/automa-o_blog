"""Aba: configurar provedores de IA e chaves de API."""

from __future__ import annotations

from nicegui import run, ui

from config.settings_store import (
    mask_key,
    normalize_lmstudio_url,
    read_env_keys,
    read_lmstudio_model,
    read_lmstudio_url,
    read_ollama_url,
    read_provider_flags,
    write_env_keys,
    write_lmstudio_settings,
    write_ollama_url,
    write_provider_flags,
)
from ui.state import refresh_ai_manager

_PROVIDER_LABELS = {
    "openai": "OpenAI",
    "anthropic": "Anthropic",
    "openrouter": "OpenRouter",
    "ollama": "Ollama (local)",
    "lmstudio": "LM Studio (local)",
}

_PROVIDER_ORDER = ("openai", "anthropic", "openrouter", "ollama", "lmstudio")


def build_tab_settings(config) -> None:
    from ui.widgets import page_header

    page_header(
        "Configuração de IA",
        "Defina chaves de API e provedores. As alterações são salvas no ficheiro .env.",
    )

    status_box = ui.column().classes("w-full mb-4")
    form_box = ui.column().classes("w-full gap-2")

    def render_status():
        status_box.clear()
        ready = config.ready_providers or []
        enabled = config.enabled_providers or []
        with status_box:
            if ready:
                ui.label(f"Prontos para uso: {', '.join(ready)}").classes("text-positive")
            elif enabled:
                ui.label(
                    "Provedores habilitados, mas sem credenciais válidas. "
                    "Configure as chaves abaixo."
                ).classes("bg-orange-100 text-orange-900 p-3 rounded w-full")
            else:
                ui.label("Nenhum provedor habilitado.").classes("text-orange-600")

    def build_form():
        form_box.clear()
        env_keys = read_env_keys()
        flags = read_provider_flags()
        ollama_url = read_ollama_url()
        lmstudio_url = read_lmstudio_url()
        lmstudio_model = read_lmstudio_model()

        inputs: dict[str, ui.input] = {}

        with form_box:
            ui.label("Chaves de API").classes("text-subtitle2 mt-2")
            for env_name, label in (
                ("OPENAI_API_KEY", "OpenAI"),
                ("ANTHROPIC_API_KEY", "Anthropic"),
                ("OPENROUTER_API_KEY", "OpenRouter"),
                ("LMSTUDIO_API_KEY", "LM Studio (opcional)"),
            ):
                masked = mask_key(env_keys.get(env_name, ""))
                if env_name == "LMSTUDIO_API_KEY":
                    hint = f"Atual: {masked}" if masked else "Opcional — LM Studio aceita qualquer valor"
                else:
                    hint = f"Atual: {masked}" if masked else "Não configurada"
                inputs[env_name] = (
                    ui.input(label, placeholder=hint)
                    .props("type=password outlined dense")
                    .classes("w-full")
                )

            ui.label("Provedores").classes("text-subtitle2 mt-4")
            checkboxes: dict[str, ui.checkbox] = {}
            for name in _PROVIDER_ORDER:
                checkboxes[name] = ui.checkbox(
                    _PROVIDER_LABELS.get(name, name),
                    value=flags.get(name, False),
                )

            ui.label("Servidores locais").classes("text-subtitle2 mt-4")
            ollama_input = ui.input(
                "Ollama — URL base",
                value=ollama_url,
            ).props("outlined dense").classes("w-full")

            ui.label(
                "Ollama usa porta 11434 — não confunda com LM Studio (1234)."
            ).classes("text-caption text-grey-7")

            lmstudio_input = ui.input(
                "LM Studio — URL base",
                value=lmstudio_url,
            ).props("outlined dense").classes("w-full")
            ui.label(
                "No LM Studio: Developer → Local Server → Start Server (porta 1234)."
            ).classes("text-caption text-grey-7")

            lmstudio_model_input = ui.input(
                "LM Studio — ID do modelo carregado",
                value=lmstudio_model,
            ).props("outlined dense").classes("w-full")
            ui.label(
                "Use o identificador exibido no LM Studio (aba Models ou em GET /v1/models)."
            ).classes("text-caption text-grey-7")

            test_select = ui.select(
                list(_PROVIDER_ORDER),
                label="Testar conexão",
                value="lmstudio",
            ).classes("w-full")
            test_result = ui.label("").classes("text-caption")
            compare_box = ui.column().classes("w-full mt-2")

            def _live_overrides(name: str) -> dict | None:
                if name == "lmstudio":
                    return {
                        "base_url": normalize_lmstudio_url(lmstudio_input.value or lmstudio_url),
                        "models": {
                            "rewrite": (lmstudio_model_input.value or lmstudio_model).strip(),
                            "blog_long": (lmstudio_model_input.value or lmstudio_model).strip(),
                        },
                    }
                if name == "ollama":
                    return {
                        "base_url": (ollama_input.value or ollama_url).strip(),
                        "models": {"rewrite": "llama3", "blog_long": "llama3"},
                    }
                return None

            async def compare_config():
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

            async def test_connection():
                test_result.text = "A testar..."
                compare_box.clear()
                name = test_select.value
                mgr = config.ai_manager
                if not mgr:
                    test_result.text = "Recarregue a configuração (Salvar) primeiro."
                    test_result.classes(replace="text-negative text-caption")
                    return
                overrides = _live_overrides(name)
                ok, msg = await run.io_bound(mgr.test_provider, name, overrides)
                test_result.text = msg
                test_result.classes(
                    replace="text-positive text-caption" if ok else "text-negative text-caption"
                )
                await compare_config()

            with ui.row().classes("gap-2"):
                ui.button("Testar", on_click=test_connection).props("outline")
                ui.button("Comparar", on_click=compare_config).props("flat")

            async def save_settings():
                updates = {}
                for env_name, inp in inputs.items():
                    val = (inp.value or "").strip()
                    if val:
                        updates[env_name] = val
                if updates:
                    write_env_keys(updates)
                write_provider_flags({n: cb.value for n, cb in checkboxes.items()})
                write_ollama_url((ollama_input.value or "").strip() or "http://localhost:11434")
                write_lmstudio_settings(
                    lmstudio_input.value or lmstudio_url,
                    (lmstudio_model_input.value or "").strip() or "local-model",
                )
                refresh_ai_manager(config)
                render_status()
                ui.notify("Configuração salva.", type="positive")
                build_form()

            ui.button("Salvar e aplicar", on_click=save_settings).props("no-caps").classes(
                "mt-4 geo-btn-primary"
            )

    render_status()
    build_form()
