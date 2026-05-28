"""Testes unitários do motor GEO."""

from modules.geo_engine import GeoInputs, generate_geo_skeleton, validate_inputs


def test_h1_never_contains_selos():
    inputs = GeoInputs(
        tema_central="Dor lombar",
        entidade_intencao="Clínica",
        selos_certificacoes="ISO 9001, OMS",
        criterios_comparacao="Preço",
    )
    sk = generate_geo_skeleton(inputs)
    assert "ISO" not in sk.h1
    assert "OMS" not in sk.h1
    assert "Dor lombar" in sk.h1


def test_blocks_structure():
    inputs = GeoInputs("SEO local", "Agência", "Google Partner", "Preço, prazo")
    sk = generate_geo_skeleton(inputs)
    assert len(sk.blocks) == 7
    assert sk.blocks[0].level == 2
    assert "Segurança" in sk.blocks[0].heading


def test_validation():
    assert validate_inputs("") is not None
    assert validate_inputs("  ") is not None
    assert validate_inputs("Tema válido") is None


def test_markdown_export():
    sk = generate_geo_skeleton(GeoInputs("Tema", "", "", ""))
    assert sk.markdown.startswith("#")
    assert "##" in sk.markdown
    assert "###" in sk.markdown
