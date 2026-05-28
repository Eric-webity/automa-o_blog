"""Pipeline de geração de matérias para blog."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from db.repository import ArticleRepository
from services.ai_manager import AIManager
from services.blog import BlogBrief, BlogPostPackage, generate_blog_post
from services.blog.brief import LONG_FORM_THRESHOLD
from services.blog.generator import generate_blog_post_async
from services.storage import save_blog_artifacts

logger = logging.getLogger(__name__)

WORD_COUNT_WARNING_RATIO = 0.85


@dataclass
class BlogResult:
    """Resultado completo da geração de matéria para blog."""

    package: BlogPostPackage
    meta_payload: dict
    md_path: str
    meta_path: str
    index_path: str | None
    article_id: int | None
    fallback_reason: str | None
    warning: str | None


def _build_fallback_reason(package: BlogPostPackage, use_llm: bool) -> str | None:
    """Mensagem quando a geração usa fallback local."""
    if not use_llm:
        if package.word_count_target >= LONG_FORM_THRESHOLD:
            return (
                "Artigo longo solicitado sem IA — resultado será rascunho local "
                "significativamente abaixo da meta."
            )
        return "Gerado em modo local (IA desativada)."
    if package.llm_error:
        return f"IA falhou: {package.llm_error}. Artigo gerado localmente."
    if use_llm and not package.used_llm:
        return "IA indisponível — artigo gerado localmente."
    return None


def _build_warning(package: BlogPostPackage) -> str | None:
    """Alerta quando a extensão fica abaixo da meta."""
    target = package.word_count_target
    actual = package.word_count_actual
    if not target or not actual:
        return None
    ratio = actual / target
    if ratio < WORD_COUNT_WARNING_RATIO:
        pct = int(ratio * 100)
        return (
            f"Extensão abaixo da meta: {actual}/{target} palavras ({pct}%). "
            "Revise ou regenere com IA."
        )
    return None


def _enrich_index_for_storage(package: BlogPostPackage) -> dict | None:
    """Inclui metadados de geração no índice persistido (métricas do dashboard)."""
    base = dict(package.ai_index or {})
    base["used_llm"] = package.used_llm
    base["generation_mode"] = package.generation_mode
    if package.provider_used:
        base["provider_used"] = package.provider_used
    return base


def _persist_article(package: BlogPostPackage, brief: BlogBrief) -> int | None:
    """Salva matéria no blog local (SQLite)."""
    try:
        repo = ArticleRepository()
        title = (package.meta_title or brief.topic).strip() or "Sem título"
        record = repo.create(
            title=title,
            markdown_content=package.markdown,
            json_index=_enrich_index_for_storage(package),
        )
        return record.id
    except Exception as exc:
        logger.exception("Falha ao salvar matéria no blog local: %s", exc)
        return None


def run_blog_pipeline(
    brief: BlogBrief,
    *,
    use_advanced: bool = True,
    use_llm: bool = True,
    provider: str | None = None,
    manager: AIManager | None = None,
    persist: bool = True,
) -> BlogResult:
    """Executa geração, artefatos em disco e persistência no blog local."""
    package = generate_blog_post(
        brief,
        use_advanced=use_advanced,
        use_llm=use_llm,
        provider=provider,
        manager=manager,
    )
    meta_payload = {
        "meta_title": package.meta_title,
        "meta_description": package.meta_description,
        "slug": package.slug,
        "keywords": package.keywords_used,
        "faq": package.faq_items,
        "word_count_target": package.word_count_target,
        "word_count_actual": package.word_count_actual,
        "generation_mode": package.generation_mode,
    }
    md_path, meta_path, index_path = save_blog_artifacts(
        package.slug, package.markdown, meta_payload, package.ai_index or None
    )
    article_id = _persist_article(package, brief) if persist else None
    return BlogResult(
        package=package,
        meta_payload=meta_payload,
        md_path=md_path,
        meta_path=meta_path,
        index_path=index_path,
        article_id=article_id,
        fallback_reason=_build_fallback_reason(package, use_llm),
        warning=_build_warning(package),
    )


async def run_blog_pipeline_async(
    brief: BlogBrief,
    *,
    use_advanced: bool = True,
    use_llm: bool = True,
    provider: str | None = None,
    manager: AIManager | None = None,
    on_progress=None,
) -> BlogResult:
    """Versão assíncrona com pipeline multi-agente quando disponível."""
    if use_llm:
        package = await generate_blog_post_async(
            brief,
            use_advanced=use_advanced,
            use_llm=True,
            provider=provider,
            manager=manager,
            on_progress=on_progress,
        )
    else:
        import asyncio

        package = await asyncio.to_thread(
            generate_blog_post,
            brief,
            use_advanced=use_advanced,
            use_llm=False,
            provider=provider,
            manager=manager,
        )

    meta_payload = {
        "meta_title": package.meta_title,
        "meta_description": package.meta_description,
        "slug": package.slug,
        "keywords": package.keywords_used,
        "faq": package.faq_items,
        "word_count_target": package.word_count_target,
        "word_count_actual": package.word_count_actual,
        "generation_mode": package.generation_mode,
    }
    md_path, meta_path, index_path = save_blog_artifacts(
        package.slug, package.markdown, meta_payload, package.ai_index or None
    )
    article_id = _persist_article(package, brief)
    return BlogResult(
        package=package,
        meta_payload=meta_payload,
        md_path=md_path,
        meta_path=meta_path,
        index_path=index_path,
        article_id=article_id,
        fallback_reason=_build_fallback_reason(package, use_llm),
        warning=_build_warning(package),
    )
