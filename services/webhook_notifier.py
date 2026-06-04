"""Notificações HTTP após eventos de geração (n8n, Zapier, etc.)."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from config.production import load_production_settings

logger = logging.getLogger(__name__)


async def send_test_webhook() -> bool:
    """Envia evento de teste para validar a configuração."""
    return await notify_article_generated(
        {
            "title": "Teste GEO Extractor",
            "article_id": None,
            "markdown_content": "# Webhook de teste\n\nConfiguração OK.",
            "test": True,
        }
    )


async def notify_article_generated(payload: dict[str, Any]) -> bool:
    """Envia webhook POST quando uma matéria é gerada."""
    settings = load_production_settings()
    if not settings.webhook_url:
        return False

    headers = {"Content-Type": "application/json"}
    if settings.webhook_secret:
        headers["X-GEO-Secret"] = settings.webhook_secret

    body = {"event": "article.generated", "data": payload}
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(settings.webhook_url, json=body, headers=headers)
            response.raise_for_status()
        logger.info("Webhook enviado para %s", settings.webhook_url)
        return True
    except httpx.HTTPError as exc:
        logger.exception("Falha ao enviar webhook: %s", exc)
        return False


async def notify_batch_completed(
    *,
    output_dir: str,
    total: int,
    succeeded: int,
    failed: int,
) -> bool:
    """Webhook após lote CSV concluído (evento ``batch.completed``)."""
    settings = load_production_settings()
    if not settings.webhook_url:
        return False

    headers = {"Content-Type": "application/json"}
    if settings.webhook_secret:
        headers["X-GEO-Secret"] = settings.webhook_secret

    body = {
        "event": "batch.completed",
        "data": {
            "output_dir": output_dir,
            "total": total,
            "succeeded": succeeded,
            "failed": failed,
        },
    }
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(settings.webhook_url, json=body, headers=headers)
            response.raise_for_status()
        logger.info("Webhook de lote enviado para %s", settings.webhook_url)
        return True
    except httpx.HTTPError as exc:
        logger.exception("Falha ao enviar webhook de lote: %s", exc)
        return False
