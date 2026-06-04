"""Exportação de FAQ em JSON-LD (SEO técnico) na UI."""

from __future__ import annotations

import json

from nicegui import ui

from core.faq_jsonld import (
    build_faq_jsonld,
    collect_faq_items,
    serialize_faq_jsonld,
    wrap_faq_jsonld_script,
)


def _page_url_from_slug(slug: str | None) -> str | None:
    s = (slug or "").strip()
    if not s:
        return None
    return f"https://example.com/{s.lstrip('/')}"


def render_faq_jsonld_export(
    *,
    faq_items: list | None,
    markdown: str,
    page_title: str = "",
    slug: str = "",
    page_url: str | None = None,
) -> bool:
    """
    Painel de exportação FAQ JSON-LD.

    Returns:
        True se há FAQ exportável; False caso contrário.
    """
    items = collect_faq_items(faq_items, markdown)
    if not items:
        ui.label(
            "Nenhum FAQ encontrado. Ative «Incluir secção de FAQ» na geração ou "
            "adicione «## Perguntas frequentes» com perguntas em ### no Markdown."
        ).classes("geo-meta-caption")
        return False

    url = page_url or _page_url_from_slug(slug)
    title = (page_title or "").strip() or None

    try:
        jsonld = build_faq_jsonld(items, page_url=url, page_name=title)
    except ValueError as exc:
        ui.label(str(exc)).classes("geo-meta-caption")
        return False

    json_text = serialize_faq_jsonld(jsonld)
    script_text = wrap_faq_jsonld_script(jsonld)
    filename = f"faq-{slug or 'artigo'}.jsonld.json"

    def _copy_json() -> None:
        ui.run_javascript(f"navigator.clipboard.writeText({json.dumps(json_text)})")
        ui.notify("JSON-LD copiado.", type="positive")

    def _copy_script() -> None:
        ui.run_javascript(f"navigator.clipboard.writeText({json.dumps(script_text)})")
        ui.notify("Bloco <script> copiado — cole no HTML da página.", type="positive")

    with ui.row().classes("w-full items-center justify-between flex-wrap gap-2 mb-2"):
        ui.label(f"{len(items)} pergunta(s) · schema.org FAQPage").classes("geo-section-desc")
        with ui.row().classes("gap-1 flex-wrap"):
            ui.button("Copiar JSON-LD", icon="content_copy", on_click=_copy_json).props(
                "flat dense no-caps color=primary"
            )
            ui.button("Copiar <script>", icon="code", on_click=_copy_script).props(
                "flat dense no-caps"
            )
            ui.button(
                "Descarregar .json",
                icon="download",
                on_click=lambda: ui.download(json_text, filename),
            ).props("flat dense no-caps")

    with ui.expansion("Pré-visualizar JSON-LD", icon="data_object", value=False).classes(
        "w-full geo-faq-jsonld-expansion"
    ):
        ui.code(json_text, language="json").classes("w-full geo-faq-jsonld-code")

    with ui.expansion("Snippet HTML (<script>)", icon="html", value=False).classes(
        "w-full geo-faq-jsonld-expansion mt-2"
    ):
        ui.code(script_text, language="html").classes("w-full geo-faq-jsonld-code")

    if url:
        ui.label(f"URL de exemplo no JSON-LD: {url}").classes("geo-meta-caption mt-2")
    ui.label(
        "Cole o JSON-LD no <head> da página ou use o plugin SEO do seu CMS. "
        "Ajuste a URL para o domínio real antes de publicar."
    ).classes("geo-meta-caption")

    return True
