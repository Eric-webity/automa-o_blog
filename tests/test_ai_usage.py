"""Testes de registo e agregação de uso de IA."""

from services.ai_usage import (
    compute_cost_usd,
    estimate_tokens_from_text,
    format_cost_usd,
    record_ai_usage,
    UsageTokens,
)
from db.repository import AiUsageRepository


def test_estimate_tokens_from_text():
    assert estimate_tokens_from_text("abcd") == 1
    assert estimate_tokens_from_text("") == 0


def test_compute_cost_openai_mini():
    cost = compute_cost_usd("openai", "gpt-4o-mini", 1000, 500)
    assert cost > 0
    assert compute_cost_usd("ollama", "llama3", 5000, 5000) == 0.0


def test_format_cost_usd():
    assert format_cost_usd(0) == "$0.00"
    assert "$" in format_cost_usd(1.25)


def test_record_and_aggregate(tmp_path, monkeypatch):
    import config.paths as paths_mod
    from db import database as db_mod

    db_path = tmp_path / "test_ai_usage.db"
    monkeypatch.setattr(paths_mod, "DB_PATH", db_path)
    monkeypatch.setattr(db_mod, "_engine", None)
    monkeypatch.setattr(db_mod, "_SessionLocal", None)
    db_mod.init_db()

    record_ai_usage(
        provider="openai",
        model="gpt-4o-mini",
        task="rewrite",
        usage=UsageTokens(100, 50, estimated=False),
        source="test",
    )
    week = AiUsageRepository().aggregate_period(days=7)
    assert week["calls"] >= 1
    assert week["total_tokens"] >= 150
    assert week["cost_usd"] >= 0

    by_prov = AiUsageRepository().totals_by_provider(days=7)
    assert by_prov[0]["provider"] == "openai"
