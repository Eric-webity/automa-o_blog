"""Métricas agregadas para dashboard e API."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from config.paths import DATA_DIR, DB_PATH, OUTPUT_DIR
from config.production import load_production_settings
from db.repository import ArticleRecord, ArticleRepository
from services.ai_manager import AIManager
from services.ai_usage import format_cost_usd, format_tokens, get_ai_usage_stats
from services.similarity_check import similarity_threshold
from services.url_cache import cache_file_count, cache_ttl_hours, is_cache_enabled


def _file_size(path: Path) -> int:
    """Tamanho de ficheiro em bytes."""
    try:
        return path.stat().st_size if path.is_file() else 0
    except OSError:
        return 0


def _dir_size(path: Path) -> int:
    """Tamanho total de diretório em bytes."""
    if not path.is_dir():
        return 0
    total = 0
    try:
        for item in path.rglob("*"):
            if item.is_file():
                total += item.stat().st_size
    except OSError:
        pass
    return total


def _format_bytes(size: int) -> str:
    """Formata bytes para exibição humana."""
    if size < 1024:
        return f"{size} B"
    if size < 1024 * 1024:
        return f"{size / 1024:.1f} KB"
    return f"{size / (1024 * 1024):.1f} MB"


def check_api_health() -> dict:
    """Verifica estado interno da API (sem HTTP)."""
    from api.routes import health

    settings = load_production_settings()
    try:
        response = health()
        return {
            "ok": response.status == "ok",
            "status": response.status,
            "version": response.version,
            "env": response.env,
            "api_enabled": settings.api_enabled,
            "api_key_configured": bool(settings.api_key),
            "require_api_key": settings.require_api_key,
        }
    except Exception as exc:
        return {
            "ok": False,
            "status": "error",
            "version": "",
            "env": settings.env,
            "api_enabled": settings.api_enabled,
            "api_key_configured": bool(settings.api_key),
            "require_api_key": settings.require_api_key,
            "error": str(exc),
        }


def _recent_summaries(records: list[ArticleRecord]) -> list[dict]:
    """Converte registos recentes para o dashboard."""
    items: list[dict] = []
    for record in records:
        created = record.created_at
        if isinstance(created, datetime) and created.tzinfo:
            created = created.replace(tzinfo=None)
        items.append(
            {
                "id": record.id,
                "title": record.title,
                "status": record.status,
                "created_at": created.strftime("%d/%m/%Y %H:%M")
                if isinstance(created, datetime)
                else str(created),
                "word_count": len((record.markdown_content or "").split()),
            }
        )
    return items


def get_dashboard_stats(*, user_id: int | None = None) -> dict:
    """Retorna estatísticas do Content Studio (por conta quando ``user_id`` é informado)."""
    repo = ArticleRepository(user_id=user_id)
    base = repo.count_stats()
    total = int(base.get("total", 0))
    llm_count = repo.count_llm_articles()
    try:
        mgr = AIManager()
        ready = mgr.list_ready_providers()
    except Exception:
        ready = []

    settings = load_production_settings()
    db_bytes = _file_size(DB_PATH)
    output_bytes = _dir_size(OUTPUT_DIR)
    ai_usage = get_ai_usage_stats()

    return {
        "total_articles": total,
        "articles_last_7_days": repo.count_since_days(7),
        "by_status": dict(base.get("by_status", {})),
        "avg_word_count": int(base.get("avg_word_count", 0)),
        "llm_articles": llm_count,
        "local_articles": max(0, total - llm_count),
        "ready_providers": ready,
        "recent_articles": _recent_summaries(repo.list_recent(5)),
        "storage_db_bytes": db_bytes,
        "storage_output_bytes": output_bytes,
        "storage_db_label": _format_bytes(db_bytes),
        "storage_output_label": _format_bytes(output_bytes),
        "api_key_configured": bool(settings.api_key),
        "webhook_configured": bool(settings.webhook_url),
        "cms_configured": bool(settings.cms_publish_url),
        "url_cache_enabled": is_cache_enabled(),
        "url_cache_entries": cache_file_count(),
        "url_cache_ttl_hours": int(cache_ttl_hours()),
        "similarity_threshold_pct": int(similarity_threshold() * 100),
        "ai_usage": ai_usage,
        "ai_cost_7d_label": format_cost_usd(
            ai_usage.get("last_7_days", {}).get("cost_usd", 0)
        ),
        "ai_tokens_7d_label": format_tokens(
            ai_usage.get("last_7_days", {}).get("total_tokens", 0)
        ),
    }
