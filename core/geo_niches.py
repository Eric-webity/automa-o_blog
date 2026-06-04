"""Modelos GEO por área — blocos prontos para saúde, finanças e SaaS."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from core.geo_engine import (
    GeoBlock,
    GeoInputs,
    GeoSkeleton,
    H1_STYLE,
    _clean,
    _fallback_criterios,
    _fallback_entidade,
    _fallback_selos,
    build_h1,
    pick_h1_style,
)

NICHE_GENERIC = "generic"
NICHE_HEALTH = "health"
NICHE_FINANCE = "finance"
NICHE_SAAS = "saas"

BlockBuilder = Callable[[str, str, str, str], list[GeoBlock]]


@dataclass(frozen=True)
class GeoNicheMeta:
    """Metadados de um modelo GEO por nicho."""

    id: str
    label: str
    description: str
    icon: str
    default_selos: str
    default_criterios: str
    default_entidade: str


def _blocks_generic(tema: str, entidade: str, selos: str, criterios: str) -> list[GeoBlock]:
    return [
        GeoBlock(level=2, heading=f"## Segurança e Confiabilidade em {entidade}"),
        GeoBlock(
            level=3,
            heading=f"### Garantias e Normas: {selos}",
            instruction=(
                "_Instrução ao redator:_ cite selos, normas (ex.: ISO), auditorias e "
                "garantias com fonte verificável. Use frases-resposta de 1–2 linhas "
                "para facilitar citação por IAs (GEO)."
            ),
        ),
        GeoBlock(level=2, heading=f"## A Ciência por trás de {tema}"),
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
        GeoBlock(level=2, heading="## Comparativo de Mercado e Alternativas"),
        GeoBlock(
            level=3,
            heading=f"### Critérios de Escolha: {criterios}",
            instruction=(
                "_Instrução ao redator:_ comparativo objetivo, prós/contras e "
                "recomendação por perfil de utilizador."
            ),
        ),
    ]


def _blocks_health(tema: str, entidade: str, selos: str, criterios: str) -> list[GeoBlock]:
    return [
        GeoBlock(
            level=2,
            heading=f"## Segurança, regulação e evidência em {entidade}",
        ),
        GeoBlock(
            level=3,
            heading=f"### Aprovações, normas e conformidade: {selos}",
            instruction=(
                "_Instrução ao redator (saúde):_ cite regulação aplicável (ex.: ANVISA, CFM, "
                "ISO 13485, OMS), limitações de uso e aviso de que o conteúdo não substitui "
                "consulta médica. Respostas diretas no primeiro parágrafo de cada bloco."
            ),
        ),
        GeoBlock(level=2, heading=f"## O que a ciência diz sobre {tema}"),
        GeoBlock(
            level=3,
            heading="### Eficácia, estudos e limitações",
            instruction=(
                "_Instrução ao redator (saúde):_ resuma evidência disponível (ensaios, "
                "diretrizes, consensos), nível de evidência, contraindicações e "
                "populações que não devem seguir a recomendação."
            ),
        ),
        GeoBlock(
            level=3,
            heading="### Protocolos, cuidados e sinais de alerta",
            instruction=(
                "_Instrução ao redator (saúde):_ descreva passos práticos, quando procurar "
                "um profissional e sinais que exigem atenção imediata."
            ),
        ),
        GeoBlock(level=2, heading="## Opções de tratamento e cuidado disponíveis"),
        GeoBlock(
            level=3,
            heading=f"### Como comparar alternativas: {criterios}",
            instruction=(
                "_Instrução ao redator (saúde):_ compare opções por eficácia, custo, "
                "acessibilidade, efeitos adversos e adequação ao perfil do paciente/leitor."
            ),
        ),
        GeoBlock(
            level=2,
            heading="## Perguntas frequentes sobre segurança e uso",
            instruction=(
                "_Instrução ao redator (saúde):_ FAQ com linguagem acessível; evite "
                "promessas de cura ou resultados garantidos."
            ),
        ),
    ]


def _blocks_finance(tema: str, entidade: str, selos: str, criterios: str) -> list[GeoBlock]:
    return [
        GeoBlock(
            level=2,
            heading=f"## Segurança, regulação e transparência em {entidade}",
        ),
        GeoBlock(
            level=3,
            heading=f"### Licenças, auditorias e proteção: {selos}",
            instruction=(
                "_Instrução ao redator (finanças):_ mencione reguladores (CVM, Bacen, SUSEP, "
                "SEC, FCA), segregação de património, FGC/SIPC quando aplicável e "
                "políticas de privacidade de dados financeiros."
            ),
        ),
        GeoBlock(level=2, heading=f"## Fundamentos de {tema}"),
        GeoBlock(
            level=3,
            heading="### Riscos, rentabilidade e cenários",
            instruction=(
                "_Instrução ao redator (finanças):_ explique risco vs. retorno, volatilidade, "
                "cenários base/otimista/pessimista e que rentabilidade passada não garante "
                "resultados futuros."
            ),
        ),
        GeoBlock(
            level=3,
            heading="### Boas práticas e erros comuns",
            instruction=(
                "_Instrução ao redator (finanças):_ checklist de hábitos saudáveis, "
                "armadilhas (alavancagem excessiva, falta de reserva) e como evitá-las."
            ),
        ),
        GeoBlock(level=2, heading="## Comparativo de produtos e serviços"),
        GeoBlock(
            level=3,
            heading=f"### Critérios de escolha: {criterios}",
            instruction=(
                "_Instrução ao redator (finanças):_ tabela ou lista comparativa por taxas, "
                "liquidez, prazo, suporte, regulamentação e adequação ao perfil do investidor."
            ),
        ),
        GeoBlock(
            level=2,
            heading="## Impostos, custos ocultos e impacto patrimonial",
            instruction=(
                "_Instrução ao redator (finanças):_ deixe explícitos custos, tributação "
                "geral e necessidade de assessoria personalizada quando relevante."
            ),
        ),
    ]


def _blocks_saas(tema: str, entidade: str, selos: str, criterios: str) -> list[GeoBlock]:
    return [
        GeoBlock(
            level=2,
            heading=f"## Confiança, segurança e compliance em {entidade}",
        ),
        GeoBlock(
            level=3,
            heading=f"### Certificações e proteção de dados: {selos}",
            instruction=(
                "_Instrução ao redator (SaaS):_ cite SOC 2, ISO 27001, GDPR/LGPD, uptime SLA, "
                "backup, SSO e políticas de retenção de dados."
            ),
        ),
        GeoBlock(level=2, heading=f"## Como {tema} resolve o problema"),
        GeoBlock(
            level=3,
            heading="### Funcionalidades, integrações e ROI",
            instruction=(
                "_Instrução ao redator (SaaS):_ ligue funcionalidades a dores do utilizador, "
                "integrações (API, webhooks, CRM) e métricas de ROI ou produtividade."
            ),
        ),
        GeoBlock(
            level=3,
            heading="### Implementação, onboarding e time-to-value",
            instruction=(
                "_Instrução ao redator (SaaS):_ descreva passos de adoção, tempo até primeiro "
                "valor, suporte e recursos de formação."
            ),
        ),
        GeoBlock(level=2, heading="## Comparativo de ferramentas e alternativas"),
        GeoBlock(
            level=3,
            heading=f"### Critérios de escolha: {criterios}",
            instruction=(
                "_Instrução ao redator (SaaS):_ compare planos, limites, escalabilidade, "
                "ecossistema de integrações e qualidade do suporte."
            ),
        ),
        GeoBlock(
            level=2,
            heading="## Preços, contratos e quando migrar",
            instruction=(
                "_Instrução ao redator (SaaS):_ transparência sobre pricing, período de "
                "teste, lock-in e sinais de que é hora de trocar de solução."
            ),
        ),
    ]


_BUILDERS: dict[str, BlockBuilder] = {
    NICHE_GENERIC: _blocks_generic,
    NICHE_HEALTH: _blocks_health,
    NICHE_FINANCE: _blocks_finance,
    NICHE_SAAS: _blocks_saas,
}

_NICHES: dict[str, GeoNicheMeta] = {
    NICHE_GENERIC: GeoNicheMeta(
        id=NICHE_GENERIC,
        label="Genérico",
        description="Estrutura GEO padrão para qualquer tema.",
        icon="category",
        default_selos="Certificações, auditorias e normas do setor",
        default_criterios="Preço, qualidade, prazo, suporte e risco",
        default_entidade="",
    ),
    NICHE_HEALTH: GeoNicheMeta(
        id=NICHE_HEALTH,
        label="Saúde",
        description="Evidência clínica, regulação e comparativo de cuidados.",
        icon="health_and_safety",
        default_selos="ANVISA, CFM, ISO 13485, diretrizes clínicas",
        default_criterios="evidência científica, custo, acesso, efeitos adversos",
        default_entidade="serviço ou clínica de saúde",
    ),
    NICHE_FINANCE: GeoNicheMeta(
        id=NICHE_FINANCE,
        label="Finanças",
        description="Regulação, risco, rentabilidade e comparativo de produtos.",
        icon="account_balance",
        default_selos="CVM, Bacen, auditoria independente, PCI-DSS",
        default_criterios="taxas, liquidez, risco, regulamentação, suporte",
        default_entidade="instituição ou plataforma financeira",
    ),
    NICHE_SAAS: GeoNicheMeta(
        id=NICHE_SAAS,
        label="SaaS",
        description="Funcionalidades, integrações, ROI e comparativo de ferramentas.",
        icon="cloud",
        default_selos="SOC 2, ISO 27001, LGPD/GDPR, SLA de uptime",
        default_criterios="preço, integrações, escalabilidade, suporte, APIs",
        default_entidade="plataforma ou software",
    ),
}


def list_niches() -> list[GeoNicheMeta]:
    """Todos os modelos disponíveis (ordem fixa para UI)."""
    order = (NICHE_GENERIC, NICHE_HEALTH, NICHE_FINANCE, NICHE_SAAS)
    return [_NICHES[nid] for nid in order if nid in _NICHES]


def get_niche(niche_id: str) -> GeoNicheMeta:
    """Metadados de um nicho; fallback para genérico."""
    return _NICHES.get((niche_id or NICHE_GENERIC).strip().lower(), _NICHES[NICHE_GENERIC])


def normalize_niche_id(niche_id: str | None) -> str:
    key = (niche_id or NICHE_GENERIC).strip().lower()
    return key if key in _BUILDERS else NICHE_GENERIC


def enrich_inputs(inputs: GeoInputs, niche_id: str | None = None) -> GeoInputs:
    """Preenche selos, critérios e entidade com defaults do nicho quando vazios."""
    niche = get_niche(normalize_niche_id(niche_id))
    tema = _clean(inputs.tema_central)
    entidade = _clean(inputs.entidade_intencao)
    selos = _clean(inputs.selos_certificacoes)
    criterios = _clean(inputs.criterios_comparacao)

    if not entidade and niche.default_entidade:
        entidade = niche.default_entidade

    return GeoInputs(
        tema_central=tema,
        entidade_intencao=_fallback_entidade(entidade, tema),
        selos_certificacoes=_fallback_selos(selos or niche.default_selos),
        criterios_comparacao=_fallback_criterios(criterios or niche.default_criterios),
    )


def build_skeleton(inputs: GeoInputs, niche_id: str | None = None) -> GeoSkeleton:
    """Gera esqueleto GEO com blocos do nicho escolhido."""
    nid = normalize_niche_id(niche_id)
    enriched = enrich_inputs(inputs, nid)
    tema = _clean(enriched.tema_central)
    entidade = enriched.entidade_intencao
    selos = enriched.selos_certificacoes
    criterios = enriched.criterios_comparacao

    h1_style: H1_STYLE = pick_h1_style(tema)
    h1 = build_h1(tema, h1_style)
    builder = _BUILDERS[nid]
    blocks = builder(tema, entidade, selos, criterios)

    lines = [h1, ""]
    for block in blocks:
        lines.append(block.heading)
        if block.instruction:
            lines.append(block.instruction)
        lines.append("")

    markdown = "\n".join(lines).rstrip() + "\n"
    return GeoSkeleton(h1=h1, blocks=tuple(blocks), markdown=markdown, h1_style=h1_style)
