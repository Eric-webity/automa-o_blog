"""Banner de aviso quando o texto está muito parecido com as fontes."""

from __future__ import annotations

from nicegui import ui

from services.blog_pipeline import BlogResult


def render_similarity_banner(result: BlogResult) -> bool:
    """
    Banner destacado de segurança editorial (originalidade vs. fontes).

    Devolve True se o aviso foi exibido.
    """
    if not result.similarity_warning:
        return False

    is_high = (result.similarity_severity or "high") == "high"
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
                ui.label(result.similarity_warning).classes("geo-similarity-banner__text")
                if result.similarity_ratio is not None:
                    ui.label(
                        f"Similaridade detetada: ~{int(result.similarity_ratio * 100)}% "
                        f"(limite editorial: {int((result.similarity_threshold or 0.85) * 100)}%)"
                    ).classes("geo-meta-caption")
                if result.similarity_excerpt:
                    ui.label(f'Trecho: "{result.similarity_excerpt}"').classes(
                        "geo-similarity-banner__excerpt"
                    )
                ui.label(
                    "Sugestão: parafraseie, resuma com palavras próprias ou cite a fonte com link."
                ).classes("geo-similarity-banner__hint")
    return True


def notify_similarity_if_needed(result: BlogResult) -> None:
    """Toast quando a similaridade com fontes excede o limiar."""
    if not result.similarity_warning:
        return
    ui.notify(
        result.similarity_warning,
        type="warning",
        multi_line=True,
        timeout=10000,
    )
