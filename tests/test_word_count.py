"""Testes de aviso de extensão (85% da meta)."""

from services.word_count import (
    WORD_COUNT_WARNING_RATIO,
    build_word_count_warning,
    is_below_word_count_target,
)


def test_below_threshold() -> None:
    assert is_below_word_count_target(1000, 2000) is True
    msg = build_word_count_warning(1000, 2000)
    assert msg is not None
    assert "Revisão recomendada" in msg
    assert "1,000" in msg


def test_at_threshold_ok() -> None:
    target = 2000
    actual = int(target * WORD_COUNT_WARNING_RATIO)
    assert is_below_word_count_target(actual, target) is False
    assert build_word_count_warning(actual, target) is None


def test_above_threshold_ok() -> None:
    assert is_below_word_count_target(1900, 2000) is False
