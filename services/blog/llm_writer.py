"""Geração de matérias via LLM (standard e chunked)."""

from __future__ import annotations

from core.geo_engine import GeoSkeleton
from core.insight_extractor import ArticleInsight
from services.ai_manager import AIManager
from .brief import BlogBrief
from .length import length_instructions, max_tokens_for_brief
from .local_writer import parse_meta_block


def build_research_block(
    brief: BlogBrief,
    insights: list[ArticleInsight],
    ai_index: dict | None = None,
) -> str:
    from core.ai_index_builder import format_ai_index_for_prompt

    lines = [
        f"## Tema principal\n{brief.topic}",
        f"## Público\n{brief.audience}",
        f"## Tom\n{brief.tone}",
        f"## Extensão alvo\n~{brief.word_count} palavras",
        f"## Keywords\n{', '.join(brief.target_keywords) or brief.topic}",
    ]
    if brief.angle:
        lines.append(f"## Ângulo editorial\n{brief.angle}")
    if brief.brand_name:
        lines.append(f"## Marca\n{brief.brand_name}")
    if brief.cta:
        lines.append(f"## CTA\n{brief.cta}")

    if insights:
        lines.append("\n## Pesquisa das referências\n")
        for ins in insights:
            lines.append(f"### {ins.title}\nURL: {ins.url}\n")
            lines.append(f"Resumo: {ins.summary}\n")
            if ins.keywords:
                lines.append("Keywords: " + ", ".join(ins.keywords[:10]) + "\n")
            for s in ins.key_sentences[:3]:
                lines.append(f"- {s}\n")
            if ins.claims:
                lines.append("Dados/afirmações: " + "; ".join(ins.claims[:3]) + "\n")
    else:
        lines.append(
            "\n## Nota\nSem URLs de referência — use conhecimento geral do tema, "
            "mas não invente estatísticas específicas sem fonte.\n"
        )

    index_block = format_ai_index_for_prompt(ai_index) if ai_index else ""
    if index_block:
        lines.append("\n" + index_block)
    return "\n".join(lines)


def _llm_task(brief: BlogBrief) -> str:
    return "blog_long" if brief.is_long_form() else "rewrite"


def generate_long_form_chunked(
    mgr: AIManager,
    brief: BlogBrief,
    insights: list[ArticleInsight],
    skeleton: GeoSkeleton,
    system: str,
    provider: str | None,
    ai_index: dict | None = None,
) -> tuple[str, str]:
    half = brief.word_count // 2
    research = build_research_block(brief, insights, ai_index)
    length = length_instructions(brief)
    tokens_half = max(4000, max_tokens_for_brief(brief) // 2)
    task = _llm_task(brief)

    prompt1 = (
        f"{research}\n\n{length}\n\n"
        f"## Esqueleto (primeira metade)\n{skeleton.markdown}\n\n"
        f"Escreva **apenas a primeira metade** da matéria (mínimo **{half} palavras**):\n"
        "- Lead completo\n"
        "- Secções H2 desde o início até ~metade do esqueleto (incluindo blocos GEO iniciais)\n"
        "- **Não** inclua FAQ, conclusão, fontes nem bloco META.\n"
        "Markdown apenas."
    )
    part1, prov = mgr.call(
        task=task,
        prompt=prompt1,
        system=system,
        max_tokens=tokens_half,
        provider=provider,
    )

    prompt2 = (
        f"{research}\n\n{length}\n\n"
        f"## Esqueleto (segunda metade)\n{skeleton.markdown}\n\n"
        f"## Texto já publicado (continuar sem repetir o lead)\n"
        f"{part1[-4000:]}\n\n"
        f"Escreva a **segunda metade** (mínimo **{half} palavras**):\n"
        "- Secções H2 restantes do esqueleto\n"
        "- FAQ (se aplicável)\n"
        "- Conclusão e CTA\n"
        "- ## Fontes consultadas\n"
        "- Bloco ---META--- JSON ---END---\n"
        "Não repita o H1 nem reescreva o lead."
    )
    part2, prov2 = mgr.call(
        task=task,
        prompt=prompt2,
        system=system,
        max_tokens=tokens_half,
        provider=provider,
    )
    combined = part1.rstrip() + "\n\n" + part2.lstrip()
    return combined, prov2 or prov


def generate_standard(
    mgr: AIManager,
    brief: BlogBrief,
    insights: list[ArticleInsight],
    skeleton: GeoSkeleton,
    system: str,
    provider: str | None,
    ai_index: dict | None = None,
) -> tuple[str, str]:
    faq_n = 8 if brief.is_long_form() else 6
    faq_instruction = (
        f"Inclua secção '## Perguntas frequentes' com {faq_n} perguntas e respostas desenvolvidas."
        if brief.include_faq
        else "Não inclua FAQ."
    )
    user_prompt = (
        f"{build_research_block(brief, insights, ai_index)}\n\n"
        f"{length_instructions(brief)}\n\n"
        f"## Esqueleto GEO (use TODOS estes headings)\n{skeleton.markdown}\n\n"
        f"{faq_instruction}\n"
        f"CTA: {brief.cta or 'nenhum'}\n"
        "Gere a matéria completa em Markdown seguida do bloco ---META--- JSON ---END---."
    )
    raw, prov = mgr.call(
        task=_llm_task(brief),
        prompt=user_prompt,
        system=system,
        max_tokens=max_tokens_for_brief(brief),
        provider=provider,
    )
    return raw, prov


def generate_with_llm(
    mgr: AIManager,
    brief: BlogBrief,
    insights: list[ArticleInsight],
    skeleton: GeoSkeleton,
    system: str,
    provider: str | None,
    ai_index: dict | None = None,
) -> tuple[str, str, str]:
    """Retorna (raw_text, provider_used, generation_mode)."""
    if brief.is_long_form():
        raw, prov = generate_long_form_chunked(
            mgr, brief, insights, skeleton, system, provider, ai_index
        )
        return raw, prov, "long_chunked"
    raw, prov = generate_standard(mgr, brief, insights, skeleton, system, provider, ai_index)
    return raw, prov, "standard"
