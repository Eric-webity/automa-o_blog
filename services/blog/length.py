"""Utilitários de extensão para matérias de blog."""

from __future__ import annotations

import re

from core.geo_engine import GeoBlock, GeoSkeleton
from .brief import BlogBrief


def count_words(text: str) -> int:
    return len(re.findall(r"\b\w+\b", text, flags=re.UNICODE))


def max_tokens_for_brief(brief: BlogBrief) -> int:
    base = int(brief.word_count * 2.4) + 800
    if brief.is_long_form():
        base = int(brief.word_count * 2.8) + 1200
    return min(16000, max(5000, base))


def length_instructions(brief: BlogBrief) -> str:
    h2 = brief.section_count()
    per = brief.words_per_section()
    lead = 150 if brief.is_long_form() else 120
    faq_n = 8 if brief.is_long_form() else 6
    faq_words = "80–120" if brief.is_long_form() else "60–90"

    lines = [
        f"## EXTENSÃO OBRIGATÓRIA: mínimo **{brief.word_count} palavras** no corpo Markdown",
        f"- Lead: **{lead}–{lead + 40}** palavras (answer-first).",
        f"- **{h2} secções H2** com **~{per} palavras** cada (mínimo 3 parágrafos densos por H2).",
        "- Use listas, tabelas comparativas ou passo a passo quando agregar valor.",
        f"- FAQ: **{faq_n}** perguntas; cada resposta com **{faq_words}** palavras.",
        "- Conclusão: **100–150** palavras.",
        "- **Proibido** resumir em uma frase o que merece um parágrafo.",
        "- Desenvolva nuances, exemplos, prós/contras e limitações.",
    ]
    if brief.is_long_form():
        lines.extend(
            [
                "- Modo **artigo longo**: inclua contexto, erros comuns, casos práticos e tendências.",
                "- Não pare antes de cumprir a contagem; prefira aprofundar secções existentes.",
            ]
        )
    return "\n".join(lines)


def expand_skeleton_for_long(brief: BlogBrief, skeleton: GeoSkeleton) -> GeoSkeleton:
    if not brief.is_long_form():
        return skeleton

    tema = brief.topic
    extra: list[GeoBlock] = [
        GeoBlock(
            level=2,
            heading=f"## O que é {tema} e por que importa agora",
            instruction=(
                "_Instrução:_ definição clara, contexto de mercado e para quem é relevante. "
                "Mínimo 350 palavras."
            ),
        ),
        GeoBlock(
            level=3,
            heading="### Benefícios e resultados esperados",
            instruction="_Instrução:_ benefícios mensuráveis e expectativas realistas.",
        ),
        GeoBlock(
            level=2,
            heading=f"## Como aplicar {tema} na prática",
            instruction="_Instrução:_ passo a passo numerado ou checklist acionável.",
        ),
        GeoBlock(
            level=2,
            heading="## Erros comuns e como evitá-los",
            instruction="_Instrução:_ 4–6 erros frequentes com correção para cada um.",
        ),
        GeoBlock(
            level=2,
            heading="## Casos de uso e exemplos reais",
            instruction="_Instrução:_ cenários por perfil de leitor; cite fontes quando houver.",
        ),
    ]
    if brief.angle in ("comparativo", "análise de mercado", "lista"):
        extra.append(
            GeoBlock(
                level=2,
                heading="## Tendências e o que observar nos próximos meses",
                instruction="_Instrução:_ sinais de mercado sem especulação vazia.",
            )
        )

    merged_blocks = tuple(extra + list(skeleton.blocks))
    lines = [skeleton.h1, ""]
    for block in merged_blocks:
        lines.append(block.heading)
        if block.instruction:
            lines.append(block.instruction)
        lines.append("")

    markdown = "\n".join(lines).rstrip() + "\n"
    return GeoSkeleton(
        h1=skeleton.h1,
        blocks=merged_blocks,
        markdown=markdown,
        h1_style=skeleton.h1_style,
    )
