"""Orquestração da geração de matérias para blog."""

from __future__ import annotations

from dataclasses import dataclass, field

from core.insight_extractor import ArticleInsight
from services.ai_manager import AIManager
from services.blog.brief import BlogBrief
from services.blog.length import count_words, expand_skeleton_for_long
from services.blog.llm_writer import generate_with_llm
from services.blog.local_writer import default_meta, parse_meta_block, slugify, write_local_article
from services.blog.prompts import build_system_prompt
from services.blog.research import collect_reference_insights, prepare_geo_context

__all__ = [
    "BlogPostPackage",
    "collect_reference_insights",
    "generate_blog_post",
    "generate_blog_post_async",
]


@dataclass
class BlogPostPackage:
    """Matéria pronta para publicar + metadados SEO."""

    markdown: str
    meta_title: str
    meta_description: str
    slug: str
    keywords_used: list[str]
    skeleton: object
    faq_items: list[dict[str, str]] = field(default_factory=list)
    used_llm: bool = False
    provider_used: str = ""
    insights: list[ArticleInsight] = field(default_factory=list)
    outline: list[str] = field(default_factory=list)
    word_count_target: int = 0
    word_count_actual: int = 0
    generation_mode: str = "standard"
    llm_error: str | None = None
    ai_index: dict = field(default_factory=dict)
    url_cache_hits: int = 0
    url_cache_misses: int = 0


def _finalize_package(
    brief: BlogBrief,
    body: str,
    meta: dict,
    *,
    skeleton: object,
    insights: list[ArticleInsight],
    ai_index: dict,
    used_llm: bool,
    provider_used: str,
    gen_mode: str,
    llm_error: str | None,
    url_cache_hits: int = 0,
    url_cache_misses: int = 0,
) -> BlogPostPackage:
    """Monta BlogPostPackage a partir do corpo e metadados."""
    if not meta:
        meta = default_meta(brief, body)

    faq_items = meta.get("faq") or []
    if not (isinstance(faq_items, list) and faq_items and isinstance(faq_items[0], dict)):
        faq_items = []
    if not faq_items:
        from core.faq_jsonld import extract_faq_from_markdown

        faq_items = extract_faq_from_markdown(body)

    return BlogPostPackage(
        markdown=body,
        meta_title=str(meta.get("meta_title", default_meta(brief, body)["meta_title"]))[:60],
        meta_description=str(meta.get("meta_description", ""))[:160],
        slug=str(meta.get("slug", slugify(brief.topic))),
        keywords_used=list(meta.get("keywords", brief.target_keywords))[:15],
        skeleton=skeleton,
        faq_items=faq_items,
        used_llm=used_llm,
        provider_used=provider_used,
        insights=insights,
        word_count_target=brief.word_count,
        word_count_actual=count_words(body),
        generation_mode=gen_mode,
        llm_error=llm_error,
        ai_index=ai_index,
        url_cache_hits=url_cache_hits,
        url_cache_misses=url_cache_misses,
    )


async def generate_blog_post_async(
    brief: BlogBrief,
    use_advanced: bool = True,
    use_llm: bool = True,
    provider: str | None = None,
    manager: AIManager | None = None,
    on_progress=None,
) -> BlogPostPackage:
    """Gera matéria sem bloquear a UI (usa thread pool)."""
    import asyncio

    from core.agents.types import AgentProgress, AgentStage

    if on_progress:
        on_progress(
            AgentProgress(
                stage=AgentStage.RESEARCHER,
                message="A gerar matéria…",
                progress=0.2,
            )
        )

    package = await asyncio.to_thread(
        generate_blog_post,
        brief,
        use_advanced=use_advanced,
        use_llm=use_llm,
        provider=provider,
        manager=manager,
    )

    if on_progress:
        on_progress(
            AgentProgress(
                stage=AgentStage.DONE,
                message="Matéria gerada.",
                progress=1.0,
            )
        )
    return package


def generate_blog_post(
    brief: BlogBrief,
    use_advanced: bool = True,
    use_llm: bool = True,
    provider: str | None = None,
    manager: AIManager | None = None,
) -> BlogPostPackage:
    """Gera matéria de forma síncrona."""
    insights, _, geo, ai_index, skeleton, url_stats = prepare_geo_context(
        brief, use_advanced=use_advanced
    )
    system = build_system_prompt()

    body = ""
    used_llm = False
    provider_used = "local"
    meta: dict = {}
    gen_mode = "local"
    llm_error: str | None = None

    if use_llm:
        mgr = manager or AIManager()
        try:
            raw, provider_used, gen_mode = generate_with_llm(
                mgr, brief, insights, skeleton, system, provider, ai_index
            )
            body, meta = parse_meta_block(raw)
            if not body.strip():
                raise ValueError("LLM retornou resposta vazia")
            used_llm = True
        except Exception as exc:
            llm_error = str(exc)

    if not body:
        body, meta, gen_mode = write_local_article(
            insights, skeleton, brief, geo.tema_central
        )

    return _finalize_package(
        brief,
        body,
        meta,
        skeleton=skeleton,
        insights=insights,
        ai_index=ai_index,
        used_llm=used_llm,
        provider_used=provider_used,
        gen_mode=gen_mode,
        llm_error=llm_error,
        url_cache_hits=url_stats.cache_hits,
        url_cache_misses=url_stats.cache_misses,
    )
