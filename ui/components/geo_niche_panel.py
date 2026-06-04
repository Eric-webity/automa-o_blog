"""Painel de seleção e pré-visualização de modelos GEO por nicho."""

from __future__ import annotations

from nicegui import ui

from core.geo_engine import GeoInputs, generate_geo_skeleton
from core.geo_niches import get_niche
from ui.constants import GEO_NICHE_DEFAULT, geo_niche_select_options


def render_geo_niche_panel(
    *,
    topic_input,
    audience_input,
    default_niche: str = GEO_NICHE_DEFAULT,
) -> ui.select:
    """Campo de nicho + expansão com pré-visualização dos blocos GEO."""
    options = geo_niche_select_options()
    default_label = next(
        (label for label, nid in options.items() if nid == default_niche),
        list(options.keys())[0],
    )

    ui.label("Área / modelo GEO").classes("geo-blog-field-label")
    niche_select = (
        ui.select(options, value=default_label, label="Nicho editorial")
        .classes("w-full geo-blog-input")
        .props("outlined dense")
    )
    meta = get_niche(default_niche)
    ui.label(meta.description).classes("geo-meta-caption mb-2")

    preview_box = ui.column().classes("w-full geo-niche-preview-box")

    def refresh_preview() -> None:
        preview_box.clear()
        niche_id = options.get(niche_select.value, GEO_NICHE_DEFAULT)
        tema = (topic_input.value or "").strip() or "Tema do artigo"
        audience = (audience_input.value or "").strip()
        geo = GeoInputs(
            tema_central=tema,
            entidade_intencao=audience,
            selos_certificacoes="",
            criterios_comparacao="",
        )
        skeleton = generate_geo_skeleton(geo, niche_id=niche_id)
        niche_meta = get_niche(niche_id)
        with preview_box:
            with ui.expansion(
                f"Blocos GEO — {niche_meta.label}",
                icon=niche_meta.icon,
                value=False,
            ).classes("w-full geo-niche-preview-expansion"):
                ui.markdown(skeleton.markdown).classes("w-full geo-niche-preview-md")

    niche_select.on("update:model-value", lambda _: refresh_preview())
    topic_input.on("update:model-value", lambda _: refresh_preview())
    audience_input.on("update:model-value", lambda _: refresh_preview())
    refresh_preview()

    return niche_select
