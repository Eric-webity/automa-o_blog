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


def generate_geo_skeleton(inputs: GeoInputs) -> GeoSkeleton:
    tema = _clean(inputs.tema_central)
    entidade = _fallback_entidade(_clean(inputs.entidade_intencao), tema)
    selos = _fallback_selos(_clean(inputs.selos_certificacoes))
    criterios = _fallback_criterios(_clean(inputs.criterios_comparacao))

    h1_style = pick_h1_style(tema)
    h1 = build_h1(tema, h1_style)

    blocks: list[GeoBlock] = [
        GeoBlock(
            level=2,
            heading=f"## Segurança e Confiabilidade em {entidade}",
        ),
        GeoBlock(
            level=3,
            heading=f"### Garantias e Normas: {selos}",
            instruction=(
                "_Instrução ao redator:_ cite selos, normas (ex.: ISO), auditorias e "
                "garantias com fonte verificável. Use frases-resposta de 1–2 linhas "
                "para facilitar citação por IAs (GEO)."
            ),
        ),
        GeoBlock(
            level=2,
            heading=f"## A Ciência por trás de {tema}",
        ),
        GeoBlock(
            level=3,
            heading="### Evidências, Métricas e Limitações",
            instruction=(
                "_Instrução ao redator:_ inclua dados mensuráveis, estudos ou benchmarks, "
                "mecanismo de ação quando aplicável, e limitações honestas. "
                "Priorize blocos de 134–167 palavras com resposta direta no primeiro parágrafo."
            ),
        ),
        GeoBlock(
            level=3,
            heading="### Melhores Práticas e Resultados Esperados",
            instruction=(
                "_Instrução ao redator:_ descreva expectativas, prazos realistas e "
                "sinais de progresso verificáveis."
            ),
        ),
        GeoBlock(
            level=2,
            heading="## Comparativo de Mercado e Alternativas",
        ),
        GeoBlock(
            level=3,
            heading=f"### Critérios de Escolha: {criterios}",
            instruction=(
                "_Instrução ao redator:_ comparativo objetivo, prós/contras e "
                "recomendação por perfil de utilizador."
            ),
        ),
    ]

    lines = [h1, ""]
    for block in blocks:
        lines.append(block.heading)
        if block.instruction:
            lines.append(block.instruction)
        lines.append("")

    markdown = "\n".join(lines).rstrip() + "\n"
    return GeoSkeleton(h1=h1, blocks=tuple(blocks), markdown=markdown, h1_style=h1_style)
