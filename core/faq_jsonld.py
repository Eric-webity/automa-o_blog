"""FAQ em JSON-LD (schema.org FAQPage) para SEO técnico."""

from __future__ import annotations

import json
import re
from typing import Any

SCHEMA_ORG = "https://schema.org"

_FAQ_SECTION = re.compile(
    r"^##\s+.*perguntas?\s+frequentes.*$",
    re.IGNORECASE | re.MULTILINE,
)
_NEXT_H2 = re.compile(r"^##\s+(?!#)", re.MULTILINE)
_H3_SPLIT = re.compile(r"^###\s+(.+)$", re.MULTILINE)


def normalize_faq_item(raw: Any) -> dict[str, str] | None:
    """Normaliza um item FAQ (metadado LLM ou API)."""
    if not isinstance(raw, dict):
        return None
    question = raw.get("question") or raw.get("pergunta") or raw.get("q")
    answer = raw.get("answer") or raw.get("resposta") or raw.get("a")
    q = " ".join(str(question or "").strip().split())
    a = " ".join(str(answer or "").strip().split())
    if q and a:
        return {"question": q, "answer": a}
    return None


def extract_faq_from_markdown(markdown: str) -> list[dict[str, str]]:
    """Extrai perguntas/respostas da secção «## Perguntas frequentes»."""
    text = (markdown or "").strip()
    if not text:
        return []

    match = _FAQ_SECTION.search(text)
    if not match:
        return []

    section = text[match.end() :]
    next_h2 = _NEXT_H2.search(section)
    if next_h2:
        section = section[: next_h2.start()]

    parts = _H3_SPLIT.split(section)
    items: list[dict[str, str]] = []
    idx = 1
    while idx + 1 < len(parts):
        question = parts[idx].strip()
        body = parts[idx + 1].strip()
        answer = re.split(r"\n###\s+", body, maxsplit=1)[0].strip()
        answer = re.sub(r"\n{2,}", "\n\n", answer)
        if question and answer:
            items.append({"question": question, "answer": answer})
        idx += 2
    return items


def collect_faq_items(
    faq_items: list[Any] | None,
    markdown: str | None = None,
) -> list[dict[str, str]]:
    """Combina FAQ do metadado com fallback por parsing do Markdown."""
    out: list[dict[str, str]] = []
    seen: set[str] = set()

    for raw in faq_items or []:
        item = normalize_faq_item(raw)
        if item and item["question"] not in seen:
            out.append(item)
            seen.add(item["question"])

    if not out and markdown:
        for item in extract_faq_from_markdown(markdown):
            if item["question"] not in seen:
                out.append(item)
                seen.add(item["question"])

    return out


def build_faq_jsonld(
    items: list[dict[str, str]],
    *,
    page_url: str | None = None,
    page_name: str | None = None,
) -> dict[str, Any]:
    """Monta documento JSON-LD FAQPage (schema.org)."""
    if not items:
        raise ValueError("É necessário pelo menos uma pergunta FAQ para JSON-LD.")

    main_entity = [
        {
            "@type": "Question",
            "name": item["question"],
            "acceptedAnswer": {
                "@type": "Answer",
                "text": item["answer"],
            },
        }
        for item in items
    ]

    data: dict[str, Any] = {
        "@context": SCHEMA_ORG,
        "@type": "FAQPage",
        "mainEntity": main_entity,
    }
    if page_url:
        data["@id"] = page_url
        data["url"] = page_url
    if page_name:
        data["name"] = page_name
    return data


def serialize_faq_jsonld(
    jsonld: dict[str, Any],
    *,
    indent: int = 2,
) -> str:
    """Serializa JSON-LD para ficheiro ou clipboard."""
    return json.dumps(jsonld, ensure_ascii=False, indent=indent) + "\n"


def wrap_faq_jsonld_script(jsonld: dict[str, Any], *, indent: int = 2) -> str:
    """Gera bloco `<script type=\"application/ld+json\">` para colar no HTML."""
    inner = json.dumps(jsonld, ensure_ascii=False, indent=indent)
    return f'<script type="application/ld+json">\n{inner}\n</script>\n'
