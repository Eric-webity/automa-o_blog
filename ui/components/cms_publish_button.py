"""Botão reutilizável para publicar matéria no CMS externo."""

from __future__ import annotations

import logging
from collections.abc import Callable

from nicegui import ui

from config.production import load_production_settings
from services.cms_publisher import publish_to_external_cms

logger = logging.getLogger(__name__)


def mount_cms_publish_button(
    *,
    get_title: Callable[[], str],
    get_markdown: Callable[[], str],
    get_meta: Callable[[], dict] | None = None,
    props: str = "outline icon=cloud_upload",
) -> None:
    """Adiciona botão «Publicar no CMS» (desativado se URL não configurada)."""

    async def _publish() -> None:
        settings = load_production_settings()
        if not settings.cms_publish_url:
            ui.notify(
                "Configure GEO_CMS_PUBLISH_URL no Dashboard → CMS externo.",
                type="warning",
            )
            return
        title = (get_title() or "").strip() or "Sem título"
        markdown = (get_markdown() or "").strip()
        if not markdown:
            ui.notify("O conteúdo está vazio.", type="warning")
            return
        meta = get_meta() if get_meta else {}
        result = await publish_to_external_cms(
            title=title,
            markdown_content=markdown,
            meta_title=meta.get("meta_title") or title,
            meta_description=meta.get("meta_description") or "",
            slug=meta.get("slug") or "",
            keywords=meta.get("keywords") or [],
        )
        if result.success:
            msg = result.message
            if result.url:
                msg += f" · {result.url}"
            ui.notify(msg, type="positive")
        else:
            ui.notify(result.message, type="negative")

    configured = bool(load_production_settings().cms_publish_url)
    btn = ui.button("Publicar no CMS externo", on_click=_publish).props(props)
    if not configured:
        btn.props("disable")
        btn.tooltip("Configure GEO_CMS_PUBLISH_URL no Dashboard")
