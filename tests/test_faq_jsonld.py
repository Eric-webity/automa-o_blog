"""Testes de exportação FAQ em JSON-LD."""

import json

from core.faq_jsonld import (
    build_faq_jsonld,
    collect_faq_items,
    extract_faq_from_markdown,
    normalize_faq_item,
    serialize_faq_jsonld,
    wrap_faq_jsonld_script,
)


def test_normalize_faq_item_aliases():
    assert normalize_faq_item({"pergunta": "Q?", "resposta": "A."}) == {
        "question": "Q?",
        "answer": "A.",
    }
    assert normalize_faq_item({"q": "X", "a": "Y"}) == {"question": "X", "answer": "Y"}
    assert normalize_faq_item({}) is None


def test_extract_faq_from_markdown():
    md = """# Título

## Intro

## Perguntas frequentes

### O que é X?

Resposta longa sobre X.

### Como usar?

Passo a passo.

## Fontes
"""
    items = extract_faq_from_markdown(md)
    assert len(items) == 2
    assert items[0]["question"] == "O que é X?"
    assert "Resposta longa" in items[0]["answer"]


def test_collect_faq_prefers_meta_then_markdown():
    meta = [{"question": "Meta Q", "answer": "Meta A"}]
    md = "## Perguntas frequentes\n\n### Outra?\n\nSim.\n"
    items = collect_faq_items(meta, md)
    assert len(items) == 1
    assert items[0]["question"] == "Meta Q"

    items2 = collect_faq_items([], md)
    assert len(items2) == 1
    assert items2[0]["question"] == "Outra?"


def test_build_faq_jsonld_schema():
    jsonld = build_faq_jsonld(
        [{"question": "Q1", "answer": "A1"}],
        page_url="https://site.com/post",
        page_name="Título",
    )
    assert jsonld["@type"] == "FAQPage"
    assert jsonld["@context"] == "https://schema.org"
    assert jsonld["url"] == "https://site.com/post"
    assert jsonld["mainEntity"][0]["acceptedAnswer"]["text"] == "A1"


def test_wrap_script_contains_json():
    jsonld = build_faq_jsonld([{"question": "Q", "answer": "A"}])
    script = wrap_faq_jsonld_script(jsonld)
    assert '<script type="application/ld+json">' in script
    inner = script.split("\n", 1)[1].rsplit("\n</script>", 1)[0]
    assert json.loads(inner)["@type"] == "FAQPage"


def test_serialize_ends_with_newline():
    data = build_faq_jsonld([{"question": "Q", "answer": "A"}])
    text = serialize_faq_jsonld(data)
    assert text.endswith("\n")
