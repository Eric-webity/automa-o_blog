"""Pipeline de geração de matérias para blog."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from db.repository import ArticleRepository
from services.ai_manager import AIManager
from services.blog import BlogBrief, BlogPostPackage, generate_blog_post
from services.blog.brief import LONG_FORM_THRESHOLD
from services.blog.generator import generate_blog_post_async
from services.article_fetcher import UrlFetchStats
from services.similarity_check import analyze_source_similarity, similarity_threshold
from services.storage import save_blog_artifacts
from services.word_count import WORD_COUNT_WARNING_RATIO, build_word_count_warning

logger = logging.getLogger(__name__)


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
    similarity_warning: str | None = None
    similarity_ratio: float | None = None
    similarity_severity: str | None = None
    similarity_excerpt: str | None = None
    similarity_threshold: float | None = None
    url_cache_message: str | None = None

    @property
    def warnings(self) -> list[str]:
        """Avisos editoriais consolidados (extensão, similaridade, etc.)."""
        items: list[str] = []
        if self.warning:
            items.append(self.warning)
        if self.similarity_warning:
            items.append(self.similarity_warning)
        return items


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
    """Alerta quando a extensão fica abaixo da meta (85%)."""
    return build_word_count_warning(
        package.word_count_actual or 0,
        package.word_count_target or 0,
    )


def _analyze_similarity(package: BlogPostPackage):
    """Análise de originalidade vs. fontes de referência."""
    return analyze_source_similarity(package.markdown, package.insights)


def _build_url_cache_message(package: BlogPostPackage) -> str | None:
    """Resumo de hits/misses do cache de URLs de referência."""
    stats = UrlFetchStats(
        cache_hits=package.url_cache_hits,
        cache_misses=package.url_cache_misses,
    )
    msg = stats.summary_message()
    return msg or None


def _finalize_blog_result(
    *,
    package: BlogPostPackage,
    meta_payload: dict,
    md_path: str,
    meta_path: str,
    index_path: str | None,
    article_id: int | None,
    use_llm: bool,
) -> BlogResult:
    """Monta BlogResult com avisos calculados."""
    similarity = _analyze_similarity(package)
    return BlogResult(
        package=package,
        meta_payload=meta_payload,
        md_path=md_path,
        meta_path=meta_path,
        index_path=index_path,
        article_id=article_id,
        fallback_reason=_build_fallback_reason(package, use_llm),
        warning=_build_warning(package),
        similarity_warning=similarity.message if similarity else None,
        similarity_ratio=similarity.ratio if similarity else None,
        similarity_severity=similarity.severity if similarity else None,
        similarity_excerpt=similarity.paragraph_excerpt if similarity else None,
        similarity_threshold=similarity_threshold(),
        url_cache_message=_build_url_cache_message(package),
    )


def _enrich_index_for_storage(package: BlogPostPackage) -> dict | None:
    """Inclui metadados de geração no índice persistido (métricas do dashboard)."""
    base = dict(package.ai_index or {})
    base["used_llm"] = package.used_llm
    base["generation_mode"] = package.generation_mode
    if package.provider_used:
        base["provider_used"] = package.provider_used
    return base


def _persist_article(
    package: BlogPostPackage,
    brief: BlogBrief,
    article_id: int | None = None,
) -> int | None:
    """Salva matéria no blog local (SQLite).

    Quando ``article_id`` é informado, atualiza o registro existente (evitando
    duplicatas ao regenerar). Se o registro não existir mais, cria um novo.
    """
    try:
        repo = ArticleRepository()
        title = (package.meta_title or brief.topic).strip() or "Sem título"
        index_payload = _enrich_index_for_storage(package)
        if article_id is not None:
            updated = repo.update(
                article_id,
                title=title,
                markdown_content=package.markdown,
                json_index=index_payload,
            )
            if updated is not None:
                return updated.id
        record = repo.create(
            title=title,
            markdown_content=package.markdown,
            json_index=index_payload,
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
    article_id: int | None = None,
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
    saved_id = _persist_article(package, brief, article_id) if persist else None
    return _finalize_blog_result(
        package=package,
        meta_payload=meta_payload,
        md_path=md_path,
        meta_path=meta_path,
        index_path=index_path,
        article_id=saved_id,
        use_llm=use_llm,
    )


async def run_blog_pipeline_async(
    brief: BlogBrief,
    *,
    use_advanced: bool = True,
    use_llm: bool = True,
    provider: str | None = None,
    manager: AIManager | None = None,
    on_progress=None,
    persist: bool = True,
    article_id: int | None = None,
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
    saved_id = _persist_article(package, brief, article_id) if persist else None
    return _finalize_blog_result(
        package=package,
        meta_payload=meta_payload,
        md_path=md_path,
        meta_path=meta_path,
        index_path=index_path,
        article_id=saved_id,
        use_llm=use_llm,
    )
