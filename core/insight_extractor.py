"""Extração de insights — modo avançado (NLP) com fallback heurístico."""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field

from services.advanced_extractor import get_extractor
from services.article_fetcher import FetchedArticle

PT_STOP = {
    "a", "o", "e", "de", "da", "do", "em", "um", "uma", "os", "as", "dos", "das",
    "para", "com", "por", "que", "na", "no", "se", "ao", "à", "é", "são", "como",
    "mais", "mas", "ou", "seu", "sua", "seus", "suas", "este", "esta", "isso",
    "ele", "ela", "eles", "elas", "já", "também", "entre", "sobre", "após", "até",
    "sem", "nos", "nas", "pelo", "pela", "pelos", "pelas", "foi", "ser", "ter",
    "há", "ainda", "muito", "pode", "podem", "quando", "onde", "qual", "quais",
}


@dataclass
class ArticleInsight:
    url: str
    domain: str
    title: str
    tema_central: str
    entidades: list[str]
    key_sentences: list[str]
    keywords: list[str]
    trust_signals: list[str]
    comparison_criteria: list[str]
    summary_bullets: list[str]
    summary: str = ""
    claims: list[str] = field(default_factory=list)
    entities_ner: dict[str, list[str]] = field(default_factory=dict)
    extraction_mode: str = "basic"


def _find_trust_signals(text: str) -> list[str]:
    patterns = [
        r"ISO\s*\d+",
        r"OMS|WHO",
        r"certificad[oa]",
        r"aprovad[oa]",
        r"ANVISA",
        r"auditoria",
        r"garantia",
    ]
    found: list[str] = []
    for pat in patterns:
        for m in re.finditer(pat, text, re.I):
            found.append(m.group(0))
    return list(dict.fromkeys(found))[:8]


def _basic_keywords(text: str, n: int = 12) -> list[str]:
    words = re.findall(r"[a-záàâãéêíóôõúçA-ZÁÀÂÃÉÊÍÓÔÕÚÇ0-9]{3,}", text.lower())
    words = [w for w in words if w not in PT_STOP]
    return [w for w, _ in Counter(words).most_common(n)]


def extract_insights(article: FetchedArticle, use_advanced: bool = True) -> ArticleInsight | None:
    if article.error or not article.text.strip():
        return None

    text = article.text
    mode = "basic"
    keywords: list[str] = []
    sentences: list[str] = []
    summary = ""
    claims: list[str] = []
    entities_ner: dict[str, list[str]] = {}
    entidades: list[str] = []

    if use_advanced:
        try:
            adv = get_extractor()
            keywords = adv.extract_key_phrases(text)
            entities_ner = adv.extract_entities(text)
            claims = adv.extract_claims(text)
            summary = adv.summarize(text, 4)
            sentences = adv.key_sentences(text, 6)
            entidades = (
                entities_ner.get("ORG", [])
                + entities_ner.get("PER", [])
                + [h for h in article.headings if h != article.title][:3]
            )
            mode = "advanced"
        except Exception:
            pass

    if not keywords:
        keywords = _basic_keywords(text)
    if not sentences:
        sentences = _split_sentences_basic(text, 6)
    if not summary:
        summary = " ".join(sentences[:2])
    if not entidades:
        entidades = [article.title] + article.headings[:4]

    tema = article.title
    if article.headings:
        alt = [h for h in article.headings if h != article.title]
        if alt:
            tema = alt[0]

    criteria_defaults = ["preço", "qualidade", "prazo", "risco", "suporte"]
    text_lower = text.lower()
    criteria = [c for c in criteria_defaults if c in text_lower] or [
        "custo-benefício",
        "qualidade",
        "confiabilidade",
    ]

    trust = _find_trust_signals(text)
    bullets = sentences[:4] if sentences else [text[:200] + "..."]

    return ArticleInsight(
        url=article.url,
        domain=article.domain,
        title=article.title,
        tema_central=tema[:120],
        entidades=list(dict.fromkeys(entidades))[:8],
        key_sentences=sentences,
        keywords=keywords,
        trust_signals=trust,
        comparison_criteria=criteria,
        summary_bullets=bullets,
        summary=summary,
        claims=claims,
        entities_ner=entities_ner,
        extraction_mode=mode,
    )


def extract_insights_from_text(
    text: str,
    title: str = "Texto manual",
    url: str = "manual://input",
    use_advanced: bool = True,
) -> ArticleInsight | None:
    art = FetchedArticle(
        url=url,
        domain="manual",
        title=title,
        text=text,
        headings=[title],
    )
    return extract_insights(art, use_advanced=use_advanced)


def _split_sentences_basic(text: str, n: int) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+", text)
    scored = [(len(p), p.strip()) for p in parts if 60 <= len(p.strip()) <= 320]
    scored.sort(reverse=True)
    out: list[str] = []
    for _, s in scored:
        if s not in out:
            out.append(s)
        if len(out) >= n:
            break
    return out


def merge_insights(items: list[ArticleInsight | None]) -> dict[str, str]:
    items = [i for i in items if i is not None]
    if not items:
        return {}
    temas = list(dict.fromkeys(i.tema_central for i in items if i.tema_central))
    entidades = list(dict.fromkeys(e for i in items for e in i.entidades))[:6]
    selos = list(dict.fromkeys(s for i in items for s in i.trust_signals))
    criterios = list(dict.fromkeys(c for i in items for c in i.comparison_criteria))

    return {
        "tema_central": temas[0] if len(temas) == 1 else " e ".join(temas[:2]),
        "entidade_intencao": ", ".join(entidades) if entidades else items[0].domain,
        "selos_certificacoes": ", ".join(selos) if selos else "",
        "criterios_comparacao": ", ".join(criterios[:5]),
    }
