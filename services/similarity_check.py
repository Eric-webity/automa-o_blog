"""Deteção de proximidade excessiva entre matéria gerada e fontes."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from difflib import SequenceMatcher

from core.insight_extractor import ArticleInsight

_DEFAULT_THRESHOLD = 0.85
_MIN_CHUNK_LEN = 80


@dataclass(frozen=True)
class SimilarityReport:
    """Resultado da análise matéria vs. fontes."""

    ratio: float
    severity: str  # "high" | "borderline"
    message: str
    paragraph_excerpt: str = ""


def similarity_threshold() -> float:
    raw = os.getenv("GEO_SIMILARITY_THRESHOLD", str(_DEFAULT_THRESHOLD))
    try:
        limit = float(raw)
    except ValueError:
        limit = _DEFAULT_THRESHOLD
    return min(0.99, max(0.5, limit))


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def _markdown_paragraphs(markdown: str) -> list[str]:
    blocks: list[str] = []
    for block in re.split(r"\n\s*\n", markdown or ""):
        line = block.strip()
        if not line or line.startswith("#"):
            continue
        plain = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", line)
        plain = re.sub(r"[*_`#>]", "", plain).strip()
        if len(plain) >= _MIN_CHUNK_LEN:
            blocks.append(plain)
    return blocks


def _source_chunks(insights: list[ArticleInsight]) -> list[str]:
    chunks: list[str] = []
    for ins in insights:
        for sent in ins.key_sentences or []:
            if len(sent) >= _MIN_CHUNK_LEN:
                chunks.append(sent)
        summary = (ins.summary or "").strip()
        if len(summary) >= _MIN_CHUNK_LEN:
            chunks.append(summary[:2000])
    return chunks


def _excerpt(text: str, max_len: int = 140) -> str:
    t = (text or "").strip()
    if len(t) <= max_len:
        return t
    return t[: max_len - 1].rstrip() + "..."


def _build_message(ratio: float, *, severity: str) -> str:
    pct = int(ratio * 100)
    if severity == "high":
        return (
            f"Texto muito parecido com uma fonte de referência (~{pct}% de similaridade). "
            "Reescreva com palavras próprias, cite a fonte ou use aspas antes de publicar."
        )
    return (
        f"Possível proximidade com fontes (~{pct}%). "
        "Releia e parafraseie os parágrafos centrais antes de publicar."
    )


def analyze_source_similarity(
    markdown: str,
    insights: list[ArticleInsight],
    *,
    threshold: float | None = None,
) -> SimilarityReport | None:
    """
    Analisa parágrafos da matéria contra trechos das fontes.

    threshold: ratio SequenceMatcher (0–1); padrão GEO_SIMILARITY_THRESHOLD ou 0.85.
    """
    if not markdown.strip() or not insights:
        return None

    limit = threshold if threshold is not None else similarity_threshold()

    paragraphs = _markdown_paragraphs(markdown)
    sources = _source_chunks(insights)
    if not paragraphs or not sources:
        return None

    best_ratio = 0.0
    best_para = ""

    for para in paragraphs:
        norm_para = _normalize(para)
        if len(norm_para) < _MIN_CHUNK_LEN:
            continue
        for src in sources:
            norm_src = _normalize(src)
            ratio = SequenceMatcher(None, norm_para, norm_src).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                best_para = para
            if ratio >= limit:
                return SimilarityReport(
                    ratio=ratio,
                    severity="high",
                    message=_build_message(ratio, severity="high"),
                    paragraph_excerpt=_excerpt(para),
                )

    if best_ratio >= limit * 0.95:
        return SimilarityReport(
            ratio=best_ratio,
            severity="borderline",
            message=_build_message(best_ratio, severity="borderline"),
            paragraph_excerpt=_excerpt(best_para),
        )
    return None


def check_source_similarity(
    markdown: str,
    insights: list[ArticleInsight],
    *,
    threshold: float | None = None,
) -> str | None:
    """Alerta textual se a matéria for muito próxima das fontes."""
    report = analyze_source_similarity(markdown, insights, threshold=threshold)
    return report.message if report else None


def _paragraph_chunks(text: str) -> list[str]:
    chunks: list[str] = []
    for block in re.split(r"\n\s*\n", text or ""):
        plain = re.sub(r"\s+", " ", block.strip())
        if len(plain) >= _MIN_CHUNK_LEN:
            chunks.append(plain[:4000])
    if not chunks and len((text or "").strip()) >= _MIN_CHUNK_LEN:
        chunks.append(re.sub(r"\s+", " ", text.strip())[:4000])
    return chunks


def analyze_pasted_text_similarity(
    generated_markdown: str,
    source_text: str,
    *,
    threshold: float | None = None,
) -> SimilarityReport | None:
    """Compara artigo gerado com o texto colado (aba Texto manual)."""
    if not generated_markdown.strip() or not source_text.strip():
        return None

    limit = threshold if threshold is not None else similarity_threshold()
    paragraphs = _markdown_paragraphs(generated_markdown)
    sources = _paragraph_chunks(source_text)
    if not paragraphs or not sources:
        return None

    best_ratio = 0.0
    best_para = ""
    for para in paragraphs:
        norm_para = _normalize(para)
        if len(norm_para) < _MIN_CHUNK_LEN:
            continue
        for src in sources:
            norm_src = _normalize(src)
            ratio = SequenceMatcher(None, norm_para, norm_src).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                best_para = para
            if ratio >= limit:
                return SimilarityReport(
                    ratio=ratio,
                    severity="high",
                    message=_build_message(ratio, severity="high"),
                    paragraph_excerpt=_excerpt(para),
                )

    if best_ratio >= limit * 0.95:
        return SimilarityReport(
            ratio=best_ratio,
            severity="borderline",
            message=_build_message(best_ratio, severity="borderline"),
            paragraph_excerpt=_excerpt(best_para),
        )
    return None
