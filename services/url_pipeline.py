"""Pipeline URL/texto → insights → índice IA → artigo GEO."""

from __future__ import annotations

from dataclasses import dataclass

from core.ai_index_builder import build_ai_index
from core.geo_engine import GeoInputs, GeoSkeleton, generate_geo_skeleton
from core.insight_extractor import ArticleInsight
from services.ai_manager import AIManager
from services.article_writer import GeneratedArticle, generate_full_article

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


def run_url_pipeline(
    insights_list: list[ArticleInsight],
    merged: dict,
    *,
    use_llm: bool = True,
    provider: str | None = None,
    manager: AIManager | None = None,
) -> UrlPipelineResult:
    geo = GeoInputs(
        tema_central=merged.get("tema_central", ""),
        entidade_intencao=merged.get("entidade_intencao", ""),
        selos_certificacoes=merged.get("selos_certificacoes", ""),
        criterios_comparacao=merged.get("criterios_comparacao", ""),
    )
    ai_index = build_ai_index(insights_list, geo.tema_central)
    skeleton = generate_geo_skeleton(geo)
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

    return UrlPipelineResult(
        merged=merged,
        insights=insights_list,
        ai_index=ai_index,
        skeleton=skeleton,
        article=article,
        index_path=index_path,
        article_path=article_path,
        fallback_reason=fallback_reason,
    )
