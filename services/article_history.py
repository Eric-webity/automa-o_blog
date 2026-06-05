"""Utilitários para persistir matérias no histórico (aprovação e metadados)."""

from __future__ import annotations

import json
from typing import Any

from db.models import ArticleStatus


def build_history_json_index(
    *,
    ai_index: dict | None = None,
    merged: dict | None = None,
    meta: dict | None = None,
    meta_title: str | None = None,
    meta_description: str | None = None,
    slug: str | None = None,
    keywords: list[str] | None = None,
    faq: list | None = None,
    extra: dict | None = None,
) -> dict:
    """Unifica índice IA, inputs GEO e metadados SEO num único payload para o SQLite."""
    payload: dict[str, Any] = {}
    if ai_index:
        payload.update(ai_index)
    if merged:
        for key, value in merged.items():
            if value is not None and key not in payload:
                payload[key] = value
    if meta:
        payload.update(meta)
    if meta_title:
        payload["meta_title"] = meta_title
    if meta_description:
        payload["meta_description"] = meta_description
    if slug:
        payload["slug"] = slug
    if keywords is not None:
        payload["keywords"] = keywords
    if faq is not None:
        payload["faq"] = faq
    if extra:
        payload.update(extra)
    return payload


def index_from_blog_package(package) -> dict:
    """Monta json_index a partir de BlogPostPackage."""
    return build_history_json_index(
        ai_index=getattr(package, "ai_index", None) or None,
        meta_title=getattr(package, "meta_title", None),
        meta_description=getattr(package, "meta_description", None),
        slug=getattr(package, "slug", None),
        keywords=getattr(package, "keywords_used", None),
        faq=getattr(package, "faq_items", None),
        extra={
            "used_llm": getattr(package, "used_llm", None),
            "generation_mode": getattr(package, "generation_mode", None),
            "provider_used": getattr(package, "provider_used", None),
            "word_count_target": getattr(package, "word_count_target", None),
            "word_count_actual": getattr(package, "word_count_actual", None),
        },
    )


def index_from_url_result(result) -> dict:
    """Monta json_index a partir de UrlPipelineResult."""
    merged = getattr(result, "merged", None) or {}
    title = (
        merged.get("tema_central")
        or merged.get("entidade_intencao")
        or "Matéria gerada a partir de URLs"
    )
    return build_history_json_index(
        ai_index=getattr(result, "ai_index", None),
        merged=merged,
        meta_title=title,
    )


def parse_import_payload(
    *,
    title: str,
    markdown: str,
    json_raw: str = "",
) -> tuple[dict | None, str | None]:
    """Valida dados colados/importados para criar matéria no histórico.

    Retorna (payload, erro). payload tem title, markdown_content, json_index, status.
    """
    clean_title = (title or "").strip()
    content = (markdown or "").strip()
    if not clean_title:
        return None, "Informe o título da matéria."
    if not content:
        return None, "Informe o conteúdo em Markdown."

    index: dict | None = None
    raw = (json_raw or "").strip()
    if raw:
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as exc:
            return None, f"JSON inválido: {exc}"
        if not isinstance(parsed, dict):
            return None, "O JSON deve ser um objeto (chaves de metadados / índice IA)."
        index = parsed

    return {
        "title": clean_title,
        "markdown_content": content,
        "json_index": index,
        "status": ArticleStatus.DRAFT.value,
    }, None
