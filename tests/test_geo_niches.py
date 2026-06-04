"""Testes dos modelos GEO por nicho (saúde, finanças, SaaS)."""

from core.geo_engine import GeoInputs, generate_geo_skeleton
from core.geo_niches import (
    NICHE_FINANCE,
    NICHE_GENERIC,
    NICHE_HEALTH,
    NICHE_SAAS,
    build_skeleton,
    enrich_inputs,
    get_niche,
    list_niches,
    normalize_niche_id,
)


def _inputs() -> GeoInputs:
    return GeoInputs(
        tema_central="Automação de marketing",
        entidade_intencao="Equipas de growth",
        selos_certificacoes="",
        criterios_comparacao="",
    )


def test_list_niches_includes_all_areas():
    ids = {n.id for n in list_niches()}
    assert ids == {NICHE_GENERIC, NICHE_HEALTH, NICHE_FINANCE, NICHE_SAAS}


def test_normalize_niche_id_fallback():
    assert normalize_niche_id("health") == NICHE_HEALTH
    assert normalize_niche_id("invalid") == NICHE_GENERIC
    assert normalize_niche_id(None) == NICHE_GENERIC


def test_enrich_inputs_uses_niche_defaults():
    geo = enrich_inputs(_inputs(), NICHE_HEALTH)
    assert "ANVISA" in geo.selos_certificacoes
    assert "evidência" in geo.criterios_comparacao.lower()


def test_generic_skeleton_has_seven_blocks():
    sk = build_skeleton(_inputs(), NICHE_GENERIC)
    assert len(sk.blocks) == 7
    assert "Segurança" in sk.blocks[0].heading


def test_health_skeleton_has_regulation_blocks():
    sk = generate_geo_skeleton(_inputs(), niche_id=NICHE_HEALTH)
    assert len(sk.blocks) == 8
    headings = " ".join(b.heading for b in sk.blocks)
    assert "ciência" in headings.lower() or "evidência" in headings.lower()
    assert any(b.instruction and "saúde" in b.instruction.lower() for b in sk.blocks)


def test_finance_skeleton_has_risk_blocks():
    sk = generate_geo_skeleton(_inputs(), niche_id=NICHE_FINANCE)
    assert len(sk.blocks) == 8
    assert get_niche(NICHE_FINANCE).icon == "account_balance"
    headings = " ".join(b.heading for b in sk.blocks)
    assert "risco" in headings.lower() or "rentabilidade" in headings.lower()


def test_saas_skeleton_has_product_blocks():
    sk = generate_geo_skeleton(_inputs(), niche_id=NICHE_SAAS)
    assert len(sk.blocks) == 8
    headings = " ".join(b.heading for b in sk.blocks)
    assert "integrações" in headings.lower() or "ROI" in headings


def test_health_markdown_includes_instructions():
    sk = build_skeleton(_inputs(), NICHE_HEALTH)
    assert sk.markdown.startswith("#")
    assert "redator (saúde)" in sk.markdown.lower()
