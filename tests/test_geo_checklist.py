"""Testes da checklist GEO (H1, FAQ, tamanho)."""

from services.blog import BlogBrief
from services.blog.generator import BlogPostPackage
from services.blog_pipeline import BlogResult
from ui.components.geo_checklist import _primary_items, evaluate_geo_checklist


def _package(**kwargs) -> BlogPostPackage:
    defaults = dict(
        markdown="# Título editorial\n\n## Secção\n\nTexto.",
        meta_title="Título SEO",
        meta_description="Descrição com tamanho suficiente para passar na validação de meta.",
        slug="titulo",
        keywords_used=["geo"],
        skeleton=object(),
        word_count_target=1000,
        word_count_actual=900,
    )
    defaults.update(kwargs)
    return BlogPostPackage(**defaults)


def test_primary_includes_h1_faq_size() -> None:
    brief = BlogBrief(topic="tema", word_count=1000, include_faq=True)
    pkg = _package(
        markdown="# Guia CRM\n\n## Perguntas frequentes\n\n### O que é?",
        faq_items=[{"question": "Q", "answer": "A"}],
    )
    result = BlogResult(
        package=pkg,
        meta_payload={},
        md_path="",
        meta_path="",
        index_path=None,
        article_id=1,
        fallback_reason=None,
        warning=None,
    )
    items = evaluate_geo_checklist(brief, pkg, result)
    primary = _primary_items(items, brief)
    ids = {i.item_id for i in primary}
    assert ids == {"word_count", "faq", "h1_editorial", "originality"}
    assert all(i.passed for i in primary)


def test_word_count_fails_below_85() -> None:
    brief = BlogBrief(topic="tema", word_count=2000, include_faq=False)
    pkg = _package(word_count_actual=1000, word_count_target=2000)
    result = BlogResult(
        package=pkg,
        meta_payload={},
        md_path="",
        meta_path="",
        index_path=None,
        article_id=None,
        fallback_reason=None,
        warning="x",
    )
    items = evaluate_geo_checklist(brief, pkg, result)
    wc = next(i for i in items if i.item_id == "word_count")
    assert wc.passed is False
