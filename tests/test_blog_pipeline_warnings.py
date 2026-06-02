"""Testes de avisos consolidados no pipeline de blog."""

from __future__ import annotations

from core.insight_extractor import ArticleInsight
from services.blog import BlogBrief
from services.blog.generator import BlogPostPackage
from services.blog_pipeline import (
    _analyze_similarity,
    _build_url_cache_message,
    _build_warning,
    _finalize_blog_result,
)
from services.word_count import WORD_COUNT_WARNING_RATIO, build_word_count_warning


def _package(**kwargs) -> BlogPostPackage:
    defaults = dict(
        markdown="# Tema\n\nConteúdo.",
        meta_title="Título SEO",
        meta_description="Descrição meta com tamanho suficiente para passar na validação editorial.",
        slug="tema",
        keywords_used=["crm"],
        skeleton=object(),
        word_count_target=2000,
        word_count_actual=1000,
        insights=[],
    )
    defaults.update(kwargs)
    return BlogPostPackage(**defaults)


def test_build_warning_below_ratio() -> None:
    pkg = _package(word_count_actual=int(2000 * (WORD_COUNT_WARNING_RATIO - 0.1)))
    msg = _build_warning(pkg)
    assert msg is not None
    assert "revisão recomendada" in msg.lower()


def test_url_cache_message_from_package() -> None:
    pkg = _package(url_cache_hits=2, url_cache_misses=0)
    msg = _build_url_cache_message(pkg)
    assert msg is not None
    assert "cache" in msg.lower()


def test_finalize_result_warnings_list() -> None:
    source = "Texto idêntico " * 15
    ins = ArticleInsight(
        url="https://x.com",
        title="X",
        domain="x.com",
        tema_central="t",
        entidades=[],
        key_sentences=[source],
        keywords=[],
        trust_signals=[],
        comparison_criteria=[],
        summary_bullets=[],
        summary=source,
        claims=[],
        extraction_mode="heuristic",
    )
    pkg = _package(
        markdown=f"# T\n\n{source}",
        word_count_actual=500,
        insights=[ins],
    )
    assert _analyze_similarity(pkg) is not None

    result = _finalize_blog_result(
        package=pkg,
        meta_payload={},
        md_path="a.md",
        meta_path="b.json",
        index_path=None,
        article_id=None,
        use_llm=True,
    )
    assert result.warning
    assert result.similarity_warning
    assert result.similarity_ratio is not None
    assert len(result.warnings) >= 2
