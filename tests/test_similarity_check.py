"""Testes de similaridade matéria vs. fontes."""

from __future__ import annotations

from core.insight_extractor import ArticleInsight
from services.similarity_check import (
    analyze_pasted_text_similarity,
    analyze_source_similarity,
    check_source_similarity,
)


def _insight(text: str) -> ArticleInsight:
    return ArticleInsight(
        url="https://example.com/a",
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


def test_no_warning_when_different() -> None:
    md = "# Título\n\nParágrafo original totalmente diferente do texto da fonte de referência usada no teste."
    msg = check_source_similarity(
        md, [_insight("Outro assunto sobre economia e mercados.")]
    )
    assert msg is None


def test_warning_when_paragraph_matches_source() -> None:
    source = (
        "O CRM aumenta a produtividade das equipas comerciais em pequenas e médias empresas "
        "através de automação de follow-up e relatórios integrados."
    )
    md = f"# Guia\n\n{source}\n\nMais texto."
    msg = check_source_similarity(md, [_insight(source)], threshold=0.85)
    assert msg is not None
    assert "parecido" in msg.lower() or "similaridade" in msg.lower()

    report = analyze_source_similarity(md, [_insight(source)], threshold=0.85)
    assert report is not None
    assert report.severity == "high"
    assert report.ratio >= 0.85
    assert report.paragraph_excerpt


def test_pasted_text_similarity_detects_copy() -> None:
    source = (
        "A automação de marketing ajuda equipas pequenas a nutrir leads "
        "com sequências personalizadas e métricas claras de conversão."
    )
    md = f"# Guia\n\n{source}\n\nConclusão breve."
    report = analyze_pasted_text_similarity(md, source, threshold=0.85)
    assert report is not None
    assert report.ratio >= 0.85


def test_pasted_text_no_warning_when_rewritten() -> None:
    source = "Texto original sobre logística portuária e contentores refrigerados."
    md = "# Novo ângulo\n\nResumo editorial distinto sobre cadeias frias e exportação."
    assert analyze_pasted_text_similarity(md, source, threshold=0.85) is None
