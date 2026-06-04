"""Banner de aviso quando o texto está muito parecido com as fontes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from nicegui import ui

from services.blog_pipeline import BlogResult
from services.similarity_check import SimilarityReport, similarity_threshold


@dataclass(frozen=True)
class SimilarityAlert:
    """Dados para exibir alerta de originalidade na UI."""

    warning: str
    severity: str = "high"
    ratio: float | None = None
    excerpt: str | None = None
    threshold: float | None = None

    @classmethod
    def from_report(cls, report: SimilarityReport | None) -> SimilarityAlert | None:
        if not report:
            return None
        return cls(
            warning=report.message,
            severity=report.severity,
            ratio=report.ratio,
            excerpt=report.paragraph_excerpt,
            threshold=similarity_threshold(),
        )

    @classmethod
    def from_blog_result(cls, result: BlogResult) -> SimilarityAlert | None:
        if not result.similarity_warning:
            return None
        return cls(
            warning=result.similarity_warning,
            severity=result.similarity_severity or "high",
            ratio=result.similarity_ratio,
            excerpt=result.similarity_excerpt,
            threshold=result.similarity_threshold,
        )

    @classmethod
    def from_url_result(cls, result: Any) -> SimilarityAlert | None:
        if not getattr(result, "similarity_warning", None):
            return None
        return cls(
            warning=result.similarity_warning,
            severity=getattr(result, "similarity_severity", None) or "high",
            ratio=getattr(result, "similarity_ratio", None),
            excerpt=getattr(result, "similarity_excerpt", None),
            threshold=getattr(result, "similarity_threshold", None),
        )


def render_similarity_banner(alert: SimilarityAlert | BlogResult | None) -> bool:
    """
    Banner destacado de segurança editorial (originalidade vs. fontes).

    Aceita ``SimilarityAlert``, ``BlogResult`` ou ``UrlPipelineResult``.
    Devolve True se o aviso foi exibido.
    """
    if alert is None:
        return False
    if isinstance(alert, BlogResult):
        info = SimilarityAlert.from_blog_result(alert)
    elif isinstance(alert, SimilarityAlert):
        info = alert
    else:
        info = SimilarityAlert.from_url_result(alert)
    if not info:
        return False

    is_high = info.severity == "high"
    title = (
        "Texto muito parecido com a fonte — reescreva antes de publicar"
        if is_high
        else "Possível cópia de fonte — revise a redação"
    )
    icon = "gpp_maybe" if is_high else "policy"
    banner_cls = (
        "geo-similarity-banner geo-similarity-banner--high"
        if is_high
        else "geo-similarity-banner geo-similarity-banner--borderline"
    )

    with ui.element("div").classes(f"{banner_cls} w-full mb-4"):
        with ui.row().classes("items-start gap-3 w-full"):
            ui.icon(icon, color="negative" if is_high else "orange").classes("mt-0.5")
            with ui.column().classes("gap-1 flex-grow min-w-0"):
                ui.label(title).classes("geo-similarity-banner__title")
                ui.label(info.warning).classes("geo-similarity-banner__text")
                if info.ratio is not None:
                    limit_pct = int((info.threshold or similarity_threshold()) * 100)
                    ui.label(
                        f"Similaridade detetada: ~{int(info.ratio * 100)}% "
                        f"(limite editorial: {limit_pct}%)"
                    ).classes("geo-meta-caption")
                if info.excerpt:
                    ui.label(f'Trecho: "{info.excerpt}"').classes(
                        "geo-similarity-banner__excerpt"
                    )
                ui.label(
                    "Sugestão: parafraseie, resuma com palavras próprias ou cite a fonte com link."
                ).classes("geo-similarity-banner__hint")
    return True


def notify_similarity_if_needed(alert: SimilarityAlert | BlogResult | None) -> None:
    """Toast quando a similaridade com fontes excede o limiar."""
    if isinstance(alert, BlogResult):
        info = SimilarityAlert.from_blog_result(alert)
    elif isinstance(alert, SimilarityAlert):
        info = alert
    elif alert is not None:
        info = SimilarityAlert.from_url_result(alert)
    else:
        info = None
    if not info:
        return
    ui.notify(info.warning, type="warning", multi_line=True, timeout=10000)
