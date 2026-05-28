"""Escrita local de matérias (sem LLM)."""

from __future__ import annotations

import json
import re

from core.geo_engine import GeoSkeleton
from core.insight_extractor import ArticleInsight
from services.article_writer import _paraphrase, write_article_local
from .brief import BlogBrief


def slugify(text: str) -> str:
    s = text.lower()
    s = re.sub(r"[áàâã]", "a", s)
    s = re.sub(r"[éê]", "e", s)
    s = re.sub(r"[í]", "i", s)
    s = re.sub(r"[óôõ]", "o", s)
    s = re.sub(r"[ú]", "u", s)
    s = re.sub(r"ç", "c", s)
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s[:80] or "artigo"


def parse_meta_block(text: str) -> tuple[str, dict]:
    pattern = r"---META---\s*(\{.*?\})\s*---END---"
    match = re.search(pattern, text, re.DOTALL)
    if not match:
        return text.strip(), {}
    try:
        meta = json.loads(match.group(1))
    except json.JSONDecodeError:
        meta = {}
    body = text[: match.start()].strip()
    return body, meta


def default_meta(brief: BlogBrief, body: str) -> dict:
    kw = brief.primary_keyword()
    title = f"{brief.topic[:50]} | Guia completo"
    if brief.brand_name:
        title = f"{brief.topic[:40]} | {brief.brand_name}"
    desc = (
        f"Descubra tudo sobre {brief.topic.lower()}: guia prático, "
        f"comparativos e respostas às dúvidas mais comuns. Leia agora."
    )[:160]
    return {
        "meta_title": title[:60],
        "meta_description": desc,
        "slug": slugify(brief.topic),
        "keywords": brief.target_keywords or [kw],
        "faq": [],
    }


def write_blog_local_long(
    insights: list[ArticleInsight],
    skeleton: GeoSkeleton,
    brief: BlogBrief,
    tema: str,
) -> str:
    body = write_article_local(insights, skeleton, tema)
    per = brief.words_per_section()
    filler_paras = [
        (
            f"Para {brief.audience.lower()}, vale cruzar informações de múltiplas fontes "
            f"antes de decidir sobre {tema.lower()}. Critérios como custo, suporte e "
            "risco regulatório costumam pesar tanto quanto o preço inicial."
        ),
        (
            f"Na prática, equipes que tratam {tema.lower()} com processo documentado "
            "reduzem retrabalho e melhoram a citabilidade do conteúdo em motores generativos."
        ),
        (
            "Compare sempre alternativas com o mesmo critério: o que funciona para um perfil "
            "pode ser inadequado para outro. Registre decisões e revise trimestralmente."
        ),
    ]
    lines = body.split("\n")
    out: list[str] = []
    para_idx = 0
    for line in lines:
        out.append(line)
        if line.startswith("## ") and not line.startswith("### "):
            for _ in range(2 if brief.is_long_form() else 1):
                out.append("")
                out.append(filler_paras[para_idx % len(filler_paras)])
                para_idx += 1
            if brief.is_long_form() and per > 350:
                out.append("")
                out.append(
                    f"**Em resumo:** este bloco sobre {line[3:].strip()} deve ser lido "
                    "como guia acionável — não apenas definição. Ajuste ao seu contexto."
                )
    return "\n".join(out)


def append_faq_local(body: str, brief: BlogBrief, insights: list[ArticleInsight]) -> str:
    if not brief.include_faq:
        return body
    tema = brief.topic
    n = 8 if brief.is_long_form() else 5
    faqs = [
        (f"O que é {tema}?", f"{tema} é um tema relevante para {brief.audience.lower()}."),
        (
            f"Como escolher a melhor opção em {tema}?",
            f"Avalie {brief.target_keywords[0] if brief.target_keywords else 'qualidade, preço e confiança'}.",
        ),
        (
            f"Vale a pena investir em {tema}?",
            "Depende do seu perfil; compare custo-benefício e fontes confiáveis antes de decidir.",
        ),
        (
            f"Quais erros evitar ao trabalhar com {tema}?",
            "Falta de critérios claros, ignorar conformidade e não comparar alternativas são os mais comuns.",
        ),
        (
            f"Quanto tempo leva para ver resultados em {tema}?",
            "Varia por contexto; defina marcos em 30, 60 e 90 dias e meça com indicadores simples.",
        ),
    ]
    while len(faqs) < n:
        faqs.append(
            (
                f"{tema}: o que muda em 2026?",
                "Tendências apontam para mais exigência de transparência, dados verificáveis e conteúdo citável por IAs.",
            )
        )
    if insights and insights[0].key_sentences:
        faqs[0] = (
            f"O que preciso saber sobre {tema}?",
            _paraphrase(insights[0].key_sentences[0])[:300],
        )
    lines = ["\n## Perguntas frequentes\n"]
    for q, a in faqs:
        lines.append(f"### {q}\n\n{a}\n")
    return body + "\n".join(lines)


def write_local_article(
    insights: list[ArticleInsight],
    skeleton: GeoSkeleton,
    brief: BlogBrief,
    tema: str,
) -> tuple[str, dict, str]:
    """Retorna (markdown, meta, generation_mode)."""
    if brief.is_long_form():
        body = write_blog_local_long(insights, skeleton, brief, tema)
        gen_mode = "local_long"
    else:
        body = write_article_local(insights, skeleton, tema)
        gen_mode = "local"
    body = append_faq_local(body, brief, insights)
    if insights:
        body += "\n## Fontes consultadas\n"
        for ins in insights:
            body += f"- [{ins.title}]({ins.url})\n"
    meta = default_meta(brief, body)
    return body, meta, gen_mode
