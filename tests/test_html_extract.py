"""Testes de extração de HTML."""

from __future__ import annotations

from services.html_extract import parse_html


def test_parse_html_extracts_title_and_paragraphs() -> None:
    html = """
    <html><head><title>Página</title></head><body>
    <h1>Título principal</h1>
    <p>Primeiro parágrafo com texto suficiente para extração editorial.</p>
    <p>Segundo parágrafo também longo o bastante para passar no filtro mínimo.</p>
    </body></html>
    """
    parsed = parse_html(html, fallback_title="fallback")
    assert parsed.title == "Título principal"
    assert "Primeiro parágrafo" in parsed.text
    assert parsed.headings
