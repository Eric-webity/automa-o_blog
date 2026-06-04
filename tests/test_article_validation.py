"""Testes de validação editorial e pré-voo do briefing."""

from __future__ import annotations

from services.article_validation import (
    evaluate_brief_preflight,
    has_blocking_issues,
    primary_checks,
    validate_article_markdown,
)
from services.url_cache import is_cache_enabled
from services.word_count import WORD_COUNT_WARNING_RATIO


def test_word_count_fails_below_ratio() -> None:
    target = 2000
    actual = int(target * WORD_COUNT_WARNING_RATIO) - 100
    items = validate_article_markdown(
        "# Título\n\n" + "palavra " * actual,
        target_words=target,
        include_faq=False,
    )
    wc = next(i for i in items if i.item_id == "word_count")
    assert wc.passed is False


def test_brief_preflight_blocks_invalid_url() -> None:
    items = evaluate_brief_preflight(
        topic="Tema",
        keywords=["a", "b"],
        reference_urls=["http://127.0.0.1/secret"],
        word_count=2500,
        use_llm=True,
    )
    urls = next(i for i in items if i.item_id == "reference_urls")
    assert urls.passed is False
    assert urls.blocking is True
    assert has_blocking_issues(items) is True


def test_brief_preflight_long_form_requires_llm() -> None:
    items = evaluate_brief_preflight(
        topic="Tema",
        keywords=["a", "b"],
        reference_urls=[],
        word_count=3000,
        use_llm=False,
    )
    lf = next(i for i in items if i.item_id == "long_form_llm")
    assert lf.passed is False


def test_brief_preflight_cache_item_when_urls_valid() -> None:
    items = evaluate_brief_preflight(
        topic="Tema",
        keywords=["a", "b"],
        reference_urls=["https://example.com/article"],
        word_count=1200,
        use_llm=True,
    )
    if not is_cache_enabled():
        assert not any(i.item_id == "reference_cache" for i in items)
        return
    cache_item = next(i for i in items if i.item_id == "reference_cache")
    assert cache_item.passed is True
    assert "URL" in cache_item.detail


def test_primary_checks_respects_faq_toggle() -> None:
    md = "# Guia\n\n## Perguntas frequentes\n\n### O que é?"
    items = validate_article_markdown(md, target_words=500, include_faq=False)
    primary = primary_checks(items, include_faq=False)
    assert "faq" not in {i.item_id for i in primary}
