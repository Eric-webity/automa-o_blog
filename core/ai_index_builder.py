"""Constrói índice estruturado no padrão JSON do Network do ChatGPT."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from core.insight_extractor import ArticleInsight


def _uuid() -> str:
    return str(uuid.uuid4())


def build_search_queries(insights: list[ArticleInsight], tema: str) -> list[dict[str, str]]:
    queries: list[str] = []
    if tema:
        queries.extend([tema, f"melhor {tema}", f"{tema} vale a pena"])
    for ins in insights:
        for kw in ins.keywords[:3]:
            queries.append(f"{kw} {ins.domain}")
    unique = list(dict.fromkeys(queries))[:10]
    return [{"q": q, "type": "search_model_query"} for q in unique]


def build_result_groups(insights: list[ArticleInsight]) -> list[dict[str, Any]]:
    groups: list[dict[str, Any]] = []
    for ins in insights:
        groups.append(
            {
                "domain": ins.domain,
                "entries": [
                    {
                        "url": ins.url,
                        "title": ins.title,
                        "snippet": (
                            ins.key_sentences[0] if ins.key_sentences else ins.tema_central
                        )[:280],
                        "domain": ins.domain,
                    }
                ],
                "type": "search_result_group",
            }
        )
    return groups


def build_ai_index(
    insights: list[ArticleInsight],
    tema: str,
    model_slug: str = "geo-extractor-indexer",
) -> dict[str, Any]:
    return {
        "status": "finished_successfully",
        "model_slug": model_slug,
        "default_model_slug": model_slug,
        "request_id": _uuid(),
        "parent_id": _uuid(),
        "turn_exchange_id": _uuid(),
        "message_type": "next",
        "recipient": "web",
        "weight": 1.0,
        "metadata": {
            "source": "geo-extractor",
            "indexed_at": datetime.now(timezone.utc).isoformat(),
            "citations": [
                {
                    "url": ins.url,
                    "title": ins.title,
                    "domain": ins.domain,
                }
                for ins in insights
            ],
            "content_references": [
                {
                    "matched_text": sent[:200],
                    "source_url": ins.url,
                    "source_domain": ins.domain,
                }
                for ins in insights
                for sent in ins.key_sentences[:2]
            ],
            "article_count": len(insights),
        },
        "search_model_queries": build_search_queries(insights, tema),
        "search_result_groups": build_result_groups(insights),
        "semantic_insights": {
            "keywords": list(dict.fromkeys(kw for ins in insights for kw in ins.keywords))[:20],
            "entities": list(dict.fromkeys(e for ins in insights for e in ins.entidades))[:15],
            "trust_signals": list(dict.fromkeys(s for ins in insights for s in ins.trust_signals)),
            "comparison_axes": list(
                dict.fromkeys(c for ins in insights for c in ins.comparison_criteria)
            ),
        },
    }


def format_ai_index_for_prompt(ai_index: dict[str, Any]) -> str:
    """Converte o índice IA em instruções aplicáveis ao redator (LLM)."""
    if not ai_index:
        return ""

    lines = [
        "## Índice IA — aplicar na redação",
        "Use estes sinais para estruturar o artigo e maximizar citabilidade por IAs:",
    ]

    queries = ai_index.get("search_model_queries") or []
    if queries:
        lines.append("\n### Consultas que a IA simularia")
        for q in queries[:8]:
            text = q.get("q") if isinstance(q, dict) else str(q)
            if text:
                lines.append(f"- Responda de forma direta a: «{text}»")

    semantic = ai_index.get("semantic_insights") or {}
    for label, key in (
        ("Keywords semânticas", "keywords"),
        ("Entidades", "entities"),
        ("Sinais de confiança", "trust_signals"),
        ("Eixos de comparação", "comparison_axes"),
    ):
        items = semantic.get(key) or []
        if items:
            lines.append(f"\n### {label}")
            lines.append(", ".join(str(x) for x in items[:12]))

    meta = ai_index.get("metadata") or {}
    citations = meta.get("citations") or []
    if citations:
        lines.append("\n### Fontes a citar (obrigatório em «Fontes consultadas»)")
        for c in citations:
            lines.append(f"- [{c.get('title', 'Fonte')}]({c.get('url', '')})")

    refs = meta.get("content_references") or []
    if refs:
        lines.append("\n### Trechos de referência (parafrasear, não copiar)")
        for r in refs[:6]:
            lines.append(f"- «{r.get('matched_text', '')[:120]}…» — {r.get('source_domain', '')}")

    lines.append(
        "\n**Regra:** distribua keywords e eixos de comparação pelos H2; "
        "inclua sinais de confiança no bloco de segurança/garantias; "
        "responda às consultas simuladas no primeiro parágrafo de cada secção relevante."
    )
    return "\n".join(lines)
