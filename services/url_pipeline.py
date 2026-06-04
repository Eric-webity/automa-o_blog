"""Pipeline URL/texto → insights → índice IA → artigo GEO."""

from __future__ import annotations

from dataclasses import dataclass

from core.ai_index_builder import build_ai_index
from core.geo_engine import GeoInputs, GeoSkeleton, generate_geo_skeleton
from core.insight_extractor import ArticleInsight
from services.ai_manager import AIManager
from services.article_writer import GeneratedArticle, generate_full_article
from services.similarity_check import analyze_source_similarity, similarity_threshold

from .storage import save_url_artifacts


@dataclass
class UrlPipelineResult:
    merged: dict
    insights: list[ArticleInsight]
    ai_index: dict
    skeleton: GeoSkeleton
    article: GeneratedArticle
    index_path: str
    article_path: str
    fallback_reason: str | None = None
    similarity_warning: str | None = None
    similarity_ratio: float | None = None
    similarity_severity: str | None = None
    similarity_excerpt: str | None = None
    similarity_threshold: float | None = None


def run_url_pipeline(
    insights_list: list[ArticleInsight],
    merged: dict,
    *,
    use_llm: bool = True,
    provider: str | None = None,
    manager: AIManager | None = None,
    geo_niche: str = "generic",
) -> UrlPipelineResult:
    from core.geo_niches import enrich_inputs, normalize_niche_id

    raw = GeoInputs(
        tema_central=merged.get("tema_central", ""),
        entidade_intencao=merged.get("entidade_intencao", ""),
        selos_certificacoes=merged.get("selos_certificacoes", ""),
        criterios_comparacao=merged.get("criterios_comparacao", ""),
    )
    niche = normalize_niche_id(merged.get("geo_niche") or geo_niche)
    geo = enrich_inputs(raw, niche)
    ai_index = build_ai_index(insights_list, geo.tema_central)
    skeleton = generate_geo_skeleton(geo, niche_id=niche)
    article = generate_full_article(
        insights_list,
        geo,
        use_llm=use_llm,
        provider=provider,
        manager=manager,
        ai_index=ai_index,
    )
    index_path, article_path = save_url_artifacts(ai_index, article.markdown)

    fallback_reason = None
    if use_llm and not article.used_llm:
        err = article.llm_error.strip()
        fallback_reason = (
            f"IA indisponível — artigo gerado em modo local. {err}"
            if err
            else "IA indisponível — artigo gerado em modo local."
        )

    similarity = analyze_source_similarity(article.markdown, insights_list)

    return UrlPipelineResult(
        merged=merged,
        insights=insights_list,
        ai_index=ai_index,
        skeleton=skeleton,
        article=article,
        index_path=index_path,
        article_path=article_path,
        fallback_reason=fallback_reason,
        similarity_warning=similarity.message if similarity else None,
        similarity_ratio=similarity.ratio if similarity else None,
        similarity_severity=similarity.severity if similarity else None,
        similarity_excerpt=similarity.paragraph_excerpt if similarity else None,
        similarity_threshold=similarity_threshold(),
    )
