"""Testes do lote CSV → Markdown."""

from pathlib import Path

import pytest

from services.batch_csv import (
    CSV_TEMPLATE,
    parse_csv_text,
    run_batch,
)
from services.blog.local_writer import slugify


def test_parse_csv_text_minimal():
    csv_text = "tema,publico\nMarketing digital,Gestores\n"
    specs, warnings = parse_csv_text(csv_text)
    assert len(specs) == 1
    assert specs[0].topic == "Marketing digital"
    assert specs[0].brief.audience == "Gestores"
    assert specs[0].file_slug == slugify("Marketing digital")
    assert not warnings


def test_parse_csv_urls_and_keywords():
    csv_text = (
        "topic,urls,keywords,faq\n"
        '"Tema X","https://a.com|https://b.com","kw1; kw2",nao\n'
    )
    specs, _ = parse_csv_text(csv_text)
    assert len(specs) == 1
    assert len(specs[0].brief.reference_urls) == 2
    assert specs[0].brief.target_keywords == ["kw1", "kw2"]
    assert specs[0].brief.include_faq is False


def test_parse_csv_requires_tema_column():
    with pytest.raises(ValueError, match="tema"):
        parse_csv_text("publico,urls\nA,B\n")


def test_parse_csv_skips_empty_tema():
    csv_text = "tema\n,\nValor\n"
    specs, warnings = parse_csv_text(csv_text)
    assert len(specs) == 1
    assert specs[0].topic == "Valor"
    assert any("vazio" in w.lower() for w in warnings)


def test_parse_csv_unique_slugs():
    csv_text = "tema,slug\nA,post\nB,post\n"
    specs, _ = parse_csv_text(csv_text)
    assert specs[0].file_slug == "post"
    assert specs[1].file_slug == "post-2"


def test_run_batch_local_writes_files(tmp_path):
    csv_text = 'tema,palavras\n"Tema lote teste",800\n'
    specs, _ = parse_csv_text(csv_text)
    result = run_batch(
        specs,
        use_llm=False,
        use_advanced=False,
        output_dir=tmp_path / "batch_test",
    )
    assert result.succeeded == 1
    assert result.failed == 0
    out = Path(result.output_dir)
    md_files = list(out.glob("*.md"))
    assert len(md_files) == 1
    assert md_files[0].read_text(encoding="utf-8").startswith("#")
    assert (out / "manifest.json").is_file()
    manifest = (out / "manifest.json").read_text(encoding="utf-8")
    assert "Tema lote teste" in manifest


def test_csv_template_parseable():
    specs, _ = parse_csv_text(CSV_TEMPLATE)
    assert len(specs) >= 2
