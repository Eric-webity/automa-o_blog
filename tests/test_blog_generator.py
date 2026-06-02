"""Testes do gerador de matérias para blog."""

from services.blog import BlogBrief, generate_blog_post
from services.blog.brief import parse_keywords
from services.blog.local_writer import slugify


def test_parse_keywords():
    assert parse_keywords("a, b; c") == ["a", "b", "c"]
    assert parse_keywords("") == []


def test_slugify():
    assert "guia-crm" in slugify("Guia CRM para PMEs")


def test_generate_blog_local_no_refs():
    brief = BlogBrief(topic="energia solar residencial", word_count=1500, include_faq=True)
    pkg = generate_blog_post(brief, use_advanced=False, use_llm=False)
    assert pkg.markdown
    assert "#" in pkg.markdown or "##" in pkg.markdown
    assert pkg.meta_title
    assert not pkg.used_llm
