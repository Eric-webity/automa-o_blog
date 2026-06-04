"""Publicação em CMS externo via endpoint HTTP configurável."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import httpx

from config.production import load_production_settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ExternalPublishResult:
    """Resultado da publicação em CMS externo."""

    success: bool
    message: str
    external_id: str | None = None
    url: str | None = None


async def publish_to_external_cms(
    *,
    title: str,
    markdown_content: str,
    meta_title: str | None = None,
    meta_description: str | None = None,
    slug: str | None = None,
    status: str | None = None,
    keywords: list[str] | None = None,
) -> ExternalPublishResult:
    """Publica artigo em URL configurada (GEO_CMS_PUBLISH_URL)."""
    settings = load_production_settings()
    if not settings.cms_publish_url:
        return ExternalPublishResult(
            success=False,
            message="GEO_CMS_PUBLISH_URL não configurada.",
        )

    payload: dict[str, Any] = {
        "title": title,
        "content": markdown_content,
        "format": "markdown",
        "status": status or settings.cms_default_status,
        "meta": {
            "title": meta_title or title,
            "description": meta_description or "",
            "slug": slug or "",
            "keywords": keywords or [],
        },
    }

    headers = {"Content-Type": "application/json"}
    if settings.cms_publish_token:
        headers["Authorization"] = f"Bearer {settings.cms_publish_token}"

    try:
        async with httpx.AsyncClient(timeout=45.0) as client:
            response = await client.post(
                settings.cms_publish_url,
                json=payload,
                headers=headers,
            )
            response.raise_for_status()
            data = response.json() if response.content else {}
        external_id = str(data.get("id", data.get("post_id", ""))) or None
        url = str(data.get("url", data.get("link", ""))) or None
        return ExternalPublishResult(
            success=True,
            message="Publicado com sucesso no CMS externo.",
            external_id=external_id,
            url=url,
        )
    except httpx.HTTPStatusError as exc:
        logger.exception("CMS retornou erro HTTP: %s", exc)
        detail = exc.response.text[:300]
        return ExternalPublishResult(
            success=False,
            message=f"CMS rejeitou publicação: {detail}",
        )
    except httpx.HTTPError as exc:
        logger.exception("Falha de conexão com CMS: %s", exc)
        return ExternalPublishResult(success=False, message=str(exc))


async def send_test_cms_publish() -> ExternalPublishResult:
    """Envia artigo de teste para validar GEO_CMS_PUBLISH_URL."""
    settings = load_production_settings()
    return await publish_to_external_cms(
        title="[GEO] Teste de CMS",
        markdown_content=(
            "# Teste GEO Extractor\n\n"
            "Publicação de teste. Pode apagar este rascunho no CMS."
        ),
        meta_description="Teste de integração com CMS externo",
        slug="geo-cms-test",
        status=settings.cms_default_status,
    )
