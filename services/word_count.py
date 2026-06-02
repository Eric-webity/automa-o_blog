"""Avisos de extensão (palavras geradas vs. meta)."""

from __future__ import annotations

WORD_COUNT_WARNING_RATIO = 0.85


def word_count_ratio(actual: int, target: int) -> float | None:
    """Rácio actual/meta, ou None se meta inválida."""
    if not target or target <= 0 or actual < 0:
        return None
    return actual / target


def is_below_word_count_target(actual: int, target: int) -> bool:
    """True quando o texto ficou abaixo de 85% da meta pedida."""
    ratio = word_count_ratio(actual, target)
    if ratio is None:
        return False
    return ratio < WORD_COUNT_WARNING_RATIO


def build_word_count_warning(actual: int, target: int) -> str | None:
    """
    Mensagem para o utilizador revisar quando a extensão fica abaixo da meta.

    Retorna None se estiver dentro do limiar (≥ 85% da meta).
    """
    ratio = word_count_ratio(actual, target)
    if ratio is None or ratio >= WORD_COUNT_WARNING_RATIO:
        return None
    pct = int(ratio * 100)
    missing = max(0, target - actual)
    return (
        f"Revisão recomendada: o texto tem {actual:,} de {target:,} palavras pedidas "
        f"({pct}% da meta, faltam cerca de {missing:,}). "
        "Expanda secções importantes ou regenere com IA antes de publicar."
    )
