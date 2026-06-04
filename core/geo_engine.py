"""
Motor de geração GEO — processamento local de estrutura de headings.

Baseado na metodologia SEO Genome (arquitetura citável por IA).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

H1_STYLE = Literal["guia", "tudo"]


@dataclass(frozen=True)
class GeoInputs:
    tema_central: str
    entidade_intencao: str
    selos_certificacoes: str
    criterios_comparacao: str


@dataclass(frozen=True)
class GeoBlock:
    level: int
    heading: str
    instruction: str | None = None


@dataclass(frozen=True)
class GeoSkeleton:
    h1: str
    blocks: tuple[GeoBlock, ...]
    markdown: str
    h1_style: H1_STYLE


def _clean(value: str) -> str:
    return " ".join(value.strip().split())


def _fallback_entidade(entidade: str, tema: str) -> str:
    return entidade if entidade else tema


def _fallback_selos(selos: str) -> str:
    if selos:
        return selos
    return "Certificações, auditorias e normas do setor (preencher com dados verificáveis)"


def _fallback_criterios(criterios: str) -> str:
    if criterios:
        return criterios
    return "Preço, qualidade, prazo, suporte e risco"


def pick_h1_style(tema: str) -> H1_STYLE:
    return "guia" if len(tema) % 2 == 0 else "tudo"


def build_h1(tema: str, style: H1_STYLE | None = None) -> str:
    chosen = style or pick_h1_style(tema)
    if chosen == "guia":
        return f"# O Guia Definitivo Sobre {tema}"
    return f"# {tema}: Tudo o que precisa de saber"


def validate_inputs(tema_central: str) -> str | None:
    if not _clean(tema_central):
        return "O campo **Tema Central** é obrigatório."
    return None


def generate_geo_skeleton(
    inputs: GeoInputs,
    niche_id: str | None = None,
) -> GeoSkeleton:
    """Gera esqueleto GEO; ``niche_id`` escolhe blocos por área (saúde, finanças, SaaS)."""
    from core.geo_niches import build_skeleton

    return build_skeleton(inputs, niche_id)
