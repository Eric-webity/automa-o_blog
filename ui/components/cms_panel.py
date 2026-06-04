"""Painel de configuração de CMS externo no dashboard."""

from __future__ import annotations

import logging

from nicegui import run, ui

from config.production import load_production_settings
from config.settings_store import mask_key, read_integration_env, write_integration_env
from services.cms_publisher import send_test_cms_publish

logger = logging.getLogger(__name__)

_STATUS_OPTIONS = {
    "Rascunho (draft)": "draft",
    "Publicado (publish)": "publish",
    "Pendente (pending)": "pending",
}


def build_cms_panel() -> None:
    """Formulário para GEO_CMS_PUBLISH_URL e teste de publicação."""
    ui.label("CMS externo").classes("text-subtitle2")
    ui.label(
        "Envia matérias via POST JSON para WordPress, Ghost, Strapi, n8n ou API própria. "
        "Use também «Publicar no CMS» no histórico ou `POST /api/v1/articles/publish`."
    ).classes("text-body2 text-grey-8")

    with ui.expansion("Formato do payload", icon="code").classes("w-full"):
        ui.markdown(
            """
```json
{
  "title": "Título",
  "content": "# Markdown…",
  "format": "markdown",
  "status": "draft",
  "meta": { "title": "…", "description": "…", "slug": "…", "keywords": [] }
}
```
Header opcional: `Authorization: Bearer <GEO_CMS_PUBLISH_TOKEN>`
            """
        ).classes("text-body2")

    env = read_integration_env()
    url_input = (
        ui.input("URL de publicação", value=env.get("GEO_CMS_PUBLISH_URL", ""))
        .classes("w-full")
        .props("outlined dense clearable")
    )
    token_input = (
        ui.input(
            "Token Bearer (opcional)",
            value=env.get("GEO_CMS_PUBLISH_TOKEN", ""),
            password=True,
            password_toggle_button=True,
        )
        .classes("w-full")
        .props("outlined dense clearable")
    )
    masked = mask_key(env.get("GEO_CMS_PUBLISH_TOKEN", ""))
    if masked:
        ui.label(f"Token atual: {masked}").classes("text-caption text-grey-7")

    current_status = (env.get("GEO_CMS_DEFAULT_STATUS") or "draft").strip()
    status_label = next(
        (k for k, v in _STATUS_OPTIONS.items() if v == current_status),
        "Rascunho (draft)",
    )
    status_select = (
        ui.select(_STATUS_OPTIONS, value=status_label, label="Estado padrão")
        .classes("w-full")
        .props("outlined dense")
    )

    status_row = ui.row().classes("gap-2 items-center mt-2")

    def _render_status() -> None:
        status_row.clear()
        settings = load_production_settings()
        with status_row:
            if settings.cms_publish_url:
                ui.html(
                    '<span class="geo-status-badge geo-status-badge--ok">'
                    "CMS configurado</span>"
                )
            else:
                ui.html(
                    '<span class="geo-status-badge geo-status-badge--warn">'
                    "CMS não configurado</span>"
                )

    async def save_cms() -> None:
        url = (url_input.value or "").strip()
        token = (token_input.value or "").strip()
        status = _STATUS_OPTIONS.get(status_select.value, "draft")
        try:
            await run.io_bound(
                write_integration_env,
                {
                    "GEO_CMS_PUBLISH_URL": url,
                    "GEO_CMS_PUBLISH_TOKEN": token,
                    "GEO_CMS_DEFAULT_STATUS": status,
                },
            )
            ui.notify("CMS salvo no .env", type="positive")
            _render_status()
        except Exception as exc:
            logger.exception("Erro ao salvar CMS: %s", exc)
            ui.notify(f"Erro ao salvar: {exc}", type="negative")

    async def test_cms() -> None:
        url = (url_input.value or "").strip()
        if not url:
            ui.notify("Informe a URL de publicação antes de testar.", type="warning")
            return
        token = (token_input.value or "").strip()
        status = _STATUS_OPTIONS.get(status_select.value, "draft")
        await run.io_bound(
            write_integration_env,
            {
                "GEO_CMS_PUBLISH_URL": url,
                "GEO_CMS_PUBLISH_TOKEN": token,
                "GEO_CMS_DEFAULT_STATUS": status,
            },
        )
        result = await send_test_cms_publish()
        if result.success:
            msg = result.message
            if result.url:
                msg += f" · {result.url}"
            ui.notify(msg, type="positive")
        else:
            ui.notify(result.message, type="negative")

    with ui.row().classes("gap-2 mt-2"):
        ui.button("Salvar CMS", icon="save", on_click=save_cms).props("color=primary")
        ui.button("Testar publicação", icon="cloud_upload", on_click=test_cms).props(
            "outline"
        )

    _render_status()
