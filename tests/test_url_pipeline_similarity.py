"""Similaridade no resultado do pipeline de URLs."""

from __future__ import annotations

from core.insight_extractor import ArticleInsight
from services.similarity_check import analyze_source_similarity


def _insight(text: str) -> ArticleInsight:
    return ArticleInsight(
        url="https://example.com/post",
        title="Fonte",
        domain="example.com",
        tema_central="tema",
        entidades=[],
        key_sentences=[text],
        keywords=[],
        trust_signals=[],
        comparison_criteria=[],
        summary_bullets=[],
        summary=text,
        claims=[],
        extraction_mode="heuristic",
    )


def test_pipeline_similarity_fields_match_analyzer() -> None:
    source = (
        "O software de gestão integra vendas, estoque e faturação "
        "para PMEs que precisam de visão única do negócio."
    )
    markdown = f"# Relatório\n\n{source}\n\nMais contexto."
    insights = [_insight(source)]
    report = analyze_source_similarity(markdown, insights, threshold=0.85)
    assert report is not None
    assert report.message
    assert report.ratio >= 0.85
