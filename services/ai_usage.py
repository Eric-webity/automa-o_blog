"""Registo e agregação de tokens/custo das chamadas de IA."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from config.paths import CONFIG_DIR
from db.repository import AiUsageRepository

logger = logging.getLogger(__name__)

_PRICING_PATH = CONFIG_DIR / "ai_pricing.yaml"
_CHARS_PER_TOKEN = 4


@dataclass(frozen=True)
class UsageTokens:
    """Contagem de tokens de uma chamada."""

    prompt_tokens: int
    completion_tokens: int
    estimated: bool = False

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens


def estimate_tokens_from_text(*parts: str | None) -> int:
    """Estimativa quando a API não devolve usage."""
    chars = sum(len(p) for p in parts if p)
    return max(0, chars // _CHARS_PER_TOKEN)


def _load_pricing() -> dict[str, Any]:
    path = _PRICING_PATH
    if not path.is_file():
        path = Path(__file__).resolve().parent.parent / "config" / "ai_pricing.yaml"
    if not path.is_file():
        return {"models": {}, "default": {"input_per_million": 1.0, "output_per_million": 3.0}}
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def compute_cost_usd(
    provider: str,
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
) -> float:
    """Calcula custo estimado em USD."""
    cfg = _load_pricing()
    if provider in (cfg.get("local_providers") or []):
        return 0.0

    models = cfg.get("models") or {}
    rates = models.get(model) or cfg.get("default") or {}
    in_rate = float(rates.get("input_per_million", 1.0))
    out_rate = float(rates.get("output_per_million", 3.0))
    cost = (prompt_tokens / 1_000_000) * in_rate + (completion_tokens / 1_000_000) * out_rate
    return round(cost, 6)


def record_ai_usage(
    *,
    provider: str,
    model: str,
    task: str,
    usage: UsageTokens | dict[str, Any] | None,
    prompt_text: str = "",
    completion_text: str = "",
    source: str = "general",
) -> None:
    """Persiste uma chamada de IA (tokens reais ou estimados)."""
    if isinstance(usage, UsageTokens):
        tokens = usage
    elif isinstance(usage, dict):
        tokens = UsageTokens(
            prompt_tokens=int(usage.get("prompt_tokens") or 0),
            completion_tokens=int(usage.get("completion_tokens") or 0),
            estimated=bool(usage.get("estimated")),
        )
    else:
        tokens = UsageTokens(0, 0, estimated=True)

    if tokens.prompt_tokens == 0 and tokens.completion_tokens == 0:
        est_in = estimate_tokens_from_text(prompt_text)
        est_out = estimate_tokens_from_text(completion_text)
        if est_in or est_out:
            tokens = UsageTokens(est_in, est_out, estimated=True)

    if tokens.total_tokens == 0:
        return

    cost = compute_cost_usd(
        provider,
        model,
        tokens.prompt_tokens,
        tokens.completion_tokens,
    )
    try:
        AiUsageRepository().insert(
            provider=provider,
            model=model,
            task=task,
            source=source,
            prompt_tokens=tokens.prompt_tokens,
            completion_tokens=tokens.completion_tokens,
            cost_usd=cost,
            estimated=tokens.estimated,
        )
    except Exception as exc:
        logger.warning("Falha ao registar uso de IA: %s", exc)


def get_ai_usage_stats() -> dict[str, Any]:
    """Métricas agregadas para o Dashboard."""
    repo = AiUsageRepository()
    today = repo.aggregate_period(days=1)
    week = repo.aggregate_period(days=7)
    month = repo.aggregate_period(days=30)
    by_provider = repo.totals_by_provider(days=30)
    recent = repo.list_recent(12)
    return {
        "today": today,
        "last_7_days": week,
        "last_30_days": month,
        "by_provider_30d": by_provider,
        "recent_calls": recent,
        "has_data": week.get("calls", 0) > 0,
    }


def format_cost_usd(value: float) -> str:
    """Formata custo para exibição."""
    if value <= 0:
        return "$0.00"
    if value < 0.01:
        return f"${value:.4f}"
    if value < 1:
        return f"${value:.3f}"
    return f"${value:.2f}"


def format_tokens(value: int) -> str:
    if value >= 1_000_000:
        return f"{value / 1_000_000:.2f}M"
    if value >= 1000:
        return f"{value / 1000:.1f}k"
    return str(value)
