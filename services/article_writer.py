"""Geração do artigo final (local ou via AIManager)."""

from __future__ import annotations

from dataclasses import dataclass

from core.geo_engine import GeoInputs, GeoSkeleton, generate_geo_skeleton
from core.insight_extractor import ArticleInsight
from services.ai_manager import AIManager

REWRITE_SYSTEM = """Você é redator especializado em GEO (Generative Engine Optimization).
Escreva em português (Brasil), tom jornalístico, artigo ORIGINAL.
Regras: H1 editorial sem siglas no título; resposta direta no 1º parágrafo de cada secção;
não copie frases das fontes; cite URLs em "Fontes consultadas" no final.
Use o esqueleto Markdown fornecido (H1, H2, H3).
NUNCA inclua instruções internas ao redator, metadados ou rótulos como "Instrução ao redator"."""


@dataclass
class GeneratedArticle:
    markdown: str
    skeleton: GeoSkeleton
    used_llm: bool
    provider_used: str = ""
    llm_error: str = ""


def _paraphrase(sentence: str) -> str:
    subs = [
        ("é importante", "vale destacar que"),
        ("segundo", "de acordo com análises sobre"),
        ("pode", "tende a"),
        ("muitos", "diversos"),
        ("também", "ademais"),
        ("porém", "contudo"),
    ]
    out = sentence
    for a, b in subs:
        out = out.replace(a, b).replace(a.capitalize(), b.capitalize())
    return out


def _build_sources_block(insights: list[ArticleInsight]) -> str:
    parts = []
    for ins in insights:
        block = [
            f"### {ins.title}",
            f"URL: {ins.url}",
            f"Resumo: {ins.summary[:400]}",
            "Frases-chave:",
            *[f"- {s}" for s in ins.key_sentences[:4]],
        ]
        if ins.claims:
            block.append("Afirmações detectadas:")
            block.extend(f"- {c}" for c in ins.claims[:3])
        parts.append("\n".join(block))
    return "\n\n".join(parts)


def _unique_sentences(insights: list[ArticleInsight]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for ins in insights:
        for sent in ins.key_sentences:
            p = _paraphrase(sent.strip())
            if p and p not in seen:
                seen.add(p)
                out.append(p)
        for claim in ins.claims:
            p = _paraphrase(claim.strip())
            if p and p not in seen:
                seen.add(p)
                out.append(p)
        if ins.summary:
            text = ins.summary[:220].strip()
            if len(text) > 40 and " " in text:
                text = text.rsplit(" ", 1)[0] + "."
            chunk = _paraphrase(text)
            if chunk and chunk not in seen:
                seen.add(chunk)
                out.append(chunk)
    return out


def write_article_local(
    insights: list[ArticleInsight],
    skeleton: GeoSkeleton,
    tema: str,
) -> str:
    if insights:
        intro = insights[0].summary or (
            insights[0].key_sentences[0] if insights[0].key_sentences else tema
        )
    else:
        intro = (
            f"Este guia reúne o essencial sobre {tema}, com foco em informação "
            "clara e verificável para leitores e motores de busca generativos."
        )
    intro = _paraphrase(intro)

    h1 = skeleton.h1 if skeleton.h1.startswith("#") else f"# {skeleton.h1.lstrip('# ')}"
    lines = [h1, ""]
    lines.append(f"**Resumo:** {_paraphrase(intro[:350])}\n")

    sentences = _unique_sentences(insights)
    sent_idx = 0

    def next_sentence() -> str | None:
        nonlocal sent_idx
        if sent_idx >= len(sentences):
            return None
        s = sentences[sent_idx]
        sent_idx += 1
        return s

    for block in skeleton.blocks:
        lines.append(f"\n{block.heading}\n")
        per_block = 2 if block.level == 2 else 1
        added = 0
        while added < per_block:
            s = next_sentence()
            if not s:
                break
            lines.append(s + "\n")
            added += 1
        if added == 0:
            lines.append(
                f"Análise editorial sobre {tema.lower()} com base nas fontes consultadas.\n"
            )

    if insights:
        lines.append("\n## Fontes consultadas\n")
        for ins in insights:
            lines.append(f"- [{ins.title}]({ins.url}) — {ins.domain}\n")
    return "\n".join(lines)


def write_article_llm(
    insights: list[ArticleInsight],
    skeleton: GeoSkeleton,
    manager: AIManager,
    provider: str | None = None,
    ai_index: dict | None = None,
) -> tuple[str, str]:
    from core.ai_index_builder import format_ai_index_for_prompt

    index_block = format_ai_index_for_prompt(ai_index) if ai_index else ""
    user = (
        f"## Esqueleto GEO\n{skeleton.markdown}\n\n"
        f"## Fontes analisadas\n{_build_sources_block(insights)}\n\n"
    )
    if index_block:
        user += f"{index_block}\n\n"
    user += "Gere o artigo completo em Markdown aplicando o Índice IA acima."
    text, used = manager.call(
        task="rewrite",
        prompt=user,
        system=REWRITE_SYSTEM,
        max_tokens=4000,
        provider=provider,
        source="url",
    )
    return text, used


def generate_full_article(
    insights: list[ArticleInsight],
    geo: GeoInputs,
    use_llm: bool = False,
    provider: str | None = None,
    manager: AIManager | None = None,
    ai_index: dict | None = None,
) -> GeneratedArticle:
    skeleton = generate_geo_skeleton(geo)

    if use_llm:
        mgr = manager or AIManager()
        try:
            md, used = write_article_llm(
                insights, skeleton, mgr, provider=provider, ai_index=ai_index
            )
            return GeneratedArticle(
                markdown=md,
                skeleton=skeleton,
                used_llm=True,
                provider_used=used,
            )
        except Exception as exc:
            llm_error = str(exc)
            md = write_article_local(insights, skeleton, geo.tema_central)
            return GeneratedArticle(
                markdown=md,
                skeleton=skeleton,
                used_llm=False,
                provider_used="local",
                llm_error=llm_error,
            )

    md = write_article_local(insights, skeleton, geo.tema_central)
    return GeneratedArticle(markdown=md, skeleton=skeleton, used_llm=False, provider_used="local")
