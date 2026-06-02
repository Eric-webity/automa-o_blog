"""Testes do Índice IA."""

from core.ai_index_builder import build_ai_index, format_ai_index_for_prompt
from core.insight_extractor import ArticleInsight


def _sample_insight() -> ArticleInsight:
    return ArticleInsight(
        url="https://example.com/artigo",
        title="Artigo teste",
        domain="example.com",
        tema_central="CRM para PMEs",
        entidades=["CRM"],
        key_sentences=["O CRM aumenta vendas em PMEs."],
        keywords=["crm", "pme", "vendas"],
        trust_signals=["ISO 27001"],
        comparison_criteria=["preco", "suporte"],
        summary_bullets=["Ponto 1"],
        summary="Resumo sobre CRM.",
        claims=["40% das PMEs usam CRM"],
        extraction_mode="heuristic",
    )


def test_build_ai_index_has_semantic_insights():
    idx = build_ai_index([_sample_insight()], "CRM para PMEs")
    assert idx["semantic_insights"]["keywords"]
    assert idx["search_model_queries"]


def test_format_ai_index_for_prompt_includes_queries_and_citations():
    idx = build_ai_index([_sample_insight()], "CRM para PMEs")
    text = format_ai_index_for_prompt(idx)
    assert "Índice IA" in text
    assert "CRM" in text
    assert "Fontes a citar" in text
