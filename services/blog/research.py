"""Coleta de referências e preparação GEO para matérias de blog."""

from __future__ import annotations

from core.ai_index_builder import build_ai_index
from core.geo_engine import GeoInputs, generate_geo_skeleton
from core.geo_niches import enrich_inputs, normalize_niche_id
from core.insight_extractor import ArticleInsight, extract_insights, merge_insights
from services.article_fetcher import UrlFetchStats, fetch_many_with_stats
from services.blog.brief import BlogBrief
from services.blog.length import expand_skeleton_for_long


def build_geo_inputs(brief: BlogBrief, merged: dict[str, str]) -> GeoInputs:
    """Monta entradas GEO a partir do briefing e insights fundidos."""
    raw = GeoInputs(
        tema_central=merged.get("tema_central", brief.topic),
        entidade_intencao=merged.get("entidade_intencao", brief.audience),
        selos_certificacoes=merged.get("selos_certificacoes", ""),
        criterios_comparacao=merged.get(
            "criterios_comparacao", ", ".join(brief.target_keywords[:4])
        ),
    )
    return enrich_inputs(raw, normalize_niche_id(brief.geo_niche))


def collect_reference_insights(
    brief: BlogBrief,
    use_advanced: bool = True,
) -> tuple[list[ArticleInsight], dict[str, str], UrlFetchStats]:
    """Obtém insights das URLs de referência e funde metadados editoriais."""
    insights: list[ArticleInsight] = []
    fetch_stats = UrlFetchStats()
    if brief.reference_urls:
        fetched, fetch_stats = fetch_many_with_stats(brief.reference_urls)
        for art in fetched:
            if art.error:
                continue
            ins = extract_insights(art, use_advanced=use_advanced)
            if ins:
                insights.append(ins)

    merged = merge_insights(insights) if insights else {}
    if not merged.get("tema_central"):
        merged["tema_central"] = brief.topic
    if brief.target_keywords and not merged.get("criterios_comparacao"):
        merged["criterios_comparacao"] = ", ".join(brief.target_keywords[:5])
    if brief.angle:
        merged["tema_central"] = f"{brief.topic} — {brief.angle}"

    return insights, merged, fetch_stats


def prepare_geo_context(
    brief: BlogBrief,
    use_advanced: bool = True,
) -> tuple[list[ArticleInsight], dict[str, str], GeoInputs, dict, object, UrlFetchStats]:
    """Executa pesquisa completa: insights, índice IA e esqueleto."""
    insights, merged, fetch_stats = collect_reference_insights(
        brief, use_advanced=use_advanced
    )
    geo = build_geo_inputs(brief, merged)
    ai_index = build_ai_index(insights, geo.tema_central)
    skeleton = generate_geo_skeleton(geo, niche_id=brief.geo_niche)
    skeleton = expand_skeleton_for_long(brief, skeleton)
    return insights, merged, geo, ai_index, skeleton, fetch_stats
