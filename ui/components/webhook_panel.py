"""Painel de configuração de webhook no dashboard."""

from __future__ import annotations

import logging

from nicegui import run, ui

from config.production import load_production_settings
from config.settings_store import mask_key, read_integration_env, write_integration_env
from services.webhook_notifier import send_test_webhook

logger = logging.getLogger(__name__)


def build_webhook_panel() -> None:
    """Formulário e guia para configurar GEO_WEBHOOK_URL."""
    ui.label("Webhook (notificações)").classes("text-subtitle2")
    ui.label(
        "Quando uma matéria é gerada pela API com «notify_webhook» ativo, "
        "o GEO Extractor envia um POST JSON para a URL configurada."
    ).classes("text-body2 text-grey-8")

    with ui.expansion("Como configurar", icon="help_outline").classes("w-full"):
        ui.markdown(
            """
**1. Escolha o destino** — qualquer serviço que aceite HTTP POST:
- [n8n](https://n8n.io) — nó *Webhook*
- [Make](https://www.make.com) — módulo *Webhooks*
- [Zapier](https://zapier.com) — trigger *Webhooks by Zapier*
- Seu backend — rota `POST /geo/article-generated`

**2. Copie a URL** do webhook que o serviço gerar (ex.: `https://hooks.n8n.cloud/webhook/abc123`).

**3. Cole abaixo** em *URL do webhook* e, se quiser, defina um *Segredo* (enviado no header `X-GEO-Secret`).

**4. Salve** e use *Testar webhook* para validar.

**Payload enviado:**
```json
{
  "event": "article.generated",
  "data": { "title": "...", "article_id": 1, "markdown_content": "..." }
}
```

Para testes locais use [webhook.site](https://webhook.site) e cole a URL única gerada.
            """
        ).classes("text-body2")

    env = read_integration_env()
    url_input = (
        ui.input("URL do webhook", value=env.get("GEO_WEBHOOK_URL", ""))
        .classes("w-full")
        .props("outlined dense clearable")
    )
    secret_input = (
        ui.input(
            "Segredo (opcional)",
            value=env.get("GEO_WEBHOOK_SECRET", ""),
            password=True,
            password_toggle_button=True,
        )
        .classes("w-full")
        .props("outlined dense clearable")
    )
    masked = mask_key(env.get("GEO_WEBHOOK_SECRET", ""))
    if masked:
        ui.label(f"Segredo atual: {masked}").classes("text-caption text-grey-7")

    status_row = ui.row().classes("gap-2 items-center mt-2")

    def _render_status() -> None:
        status_row.clear()
        settings = load_production_settings()
        with status_row:
            if settings.webhook_url:
                ui.html('<span class="geo-status-badge geo-status-badge--ok">Webhook configurado</span>')
            else:
                ui.html('<span class="geo-status-badge geo-status-badge--warn">Webhook não configurado</span>')

    async def save_webhook() -> None:
        url = (url_input.value or "").strip()
        secret = (secret_input.value or "").strip()
        try:
            await run.io_bound(
                write_integration_env,
                {
                    "GEO_WEBHOOK_URL": url,
                    "GEO_WEBHOOK_SECRET": secret,
                },
            )
            ui.notify("Webhook salvo no .env", type="positive")
            _render_status()
        except Exception as exc:
            logger.exception("Erro ao salvar webhook: %s", exc)
            ui.notify(f"Erro ao salvar: {exc}", type="negative")

    async def test_webhook() -> None:
        url = (url_input.value or "").strip()
        if not url:
            ui.notify("Informe a URL do webhook antes de testar.", type="warning")
            return
        secret = (secret_input.value or "").strip()
        if secret:
            await run.io_bound(
                write_integration_env,
                {"GEO_WEBHOOK_URL": url, "GEO_WEBHOOK_SECRET": secret},
            )
        ok = await send_test_webhook()
        if ok:
            ui.notify("Webhook de teste enviado com sucesso.", type="positive")
        else:
            ui.notify("Falha ao enviar webhook. Verifique a URL e a rede.", type="negative")

    with ui.row().classes("gap-2 mt-2"):
        ui.button("Salvar webhook", icon="save", on_click=save_webhook).props("color=primary")
        ui.button("Testar webhook", icon="send", on_click=test_webhook).props("outline")

    _render_status()
