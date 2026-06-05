"""Testes de importação e índice do histórico."""

from services.article_history import build_history_json_index, parse_import_payload


def test_build_history_json_index_merges_meta() -> None:
    payload = build_history_json_index(
        ai_index={"topic": "GEO"},
        merged={"tema_central": "Tema"},
        meta_title="Título SEO",
        faq=[{"q": "P?", "a": "R."}],
    )
    assert payload["topic"] == "GEO"
    assert payload["tema_central"] == "Tema"
    assert payload["meta_title"] == "Título SEO"
    assert payload["faq"] == [{"q": "P?", "a": "R."}]


def test_parse_import_payload_requires_fields() -> None:
    data, err = parse_import_payload(title="", markdown="# x")
    assert data is None
    assert err


def test_parse_import_payload_ok() -> None:
    data, err = parse_import_payload(
        title="Artigo",
        markdown="# Olá",
        json_raw='{"slug": "ola"}',
    )
    assert err is None
    assert data is not None
    assert data["title"] == "Artigo"
    assert data["json_index"]["slug"] == "ola"
    assert data["status"] == "draft"
