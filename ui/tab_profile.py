"""Aba: perfil do utilizador e do blog local."""

from __future__ import annotations

import logging

from nicegui import ui

from db.repository import BlogProfileRepository, BlogProfileRecord
from ui.widgets import geo_input, geo_textarea, page_header

logger = logging.getLogger(__name__)


def _field(record: BlogProfileRecord | None, attr: str) -> str:
    if record is None:
        return ""
    return getattr(record, attr, "") or ""


def build_tab_profile(config) -> None:
    """Exibe e permite editar dados pessoais e metadados do blog."""
    page_header(
        "Perfil",
        "Atualize os seus dados pessoais e as informações públicas do blog.",
        eyebrow="Conta",
    )

    repo = BlogProfileRepository()
    record = repo.get_profile()

    with ui.column().classes("geo-profile-page w-full gap-6"):
        ui.label("Dados pessoais").classes("text-subtitle1 text-weight-medium")
        name_input = geo_input("Nome completo", value=_field(record, "name"))
        email_input = geo_input(
            "Email",
            value=_field(record, "email"),
            placeholder="seu@email.com",
        )
        phone_input = geo_input(
            "Telefone (opcional)",
            value=_field(record, "phone"),
            placeholder="+351 912 345 678",
        )
        bio_input = geo_textarea(
            "Biografia / apresentação (opcional)",
            value=_field(record, "bio"),
            rows=4,
            placeholder="Breve descrição sobre si ou a sua marca.",
        )

        ui.separator()
        ui.label("Blog local").classes("text-subtitle1 text-weight-medium")
        ui.label(
            "Título e descrição usados na identidade do blog ao publicar matérias."
        ).classes("geo-page-desc !mt-0")
        blog_title_input = geo_input(
            "Título do blog",
            value=_field(record, "title"),
        )
        blog_desc_input = geo_textarea(
            "Descrição do blog",
            value=_field(record, "description"),
            rows=4,
        )

        def save_profile() -> None:
            email = (email_input.value or "").strip()
            if email and "@" not in email:
                ui.notify("Indique um email válido.", color="orange")
                return
            new_record = BlogProfileRecord(
                id=record.id if record else None,
                name=name_input.value or "",
                email=email,
                phone=phone_input.value or "",
                bio=bio_input.value or "",
                title=blog_title_input.value or "",
                description=blog_desc_input.value or "",
            )
            repo.save_profile(new_record)
            ui.notify("Perfil salvo com sucesso!", color="green")

        ui.button("Salvar perfil", on_click=save_profile).classes("self-end")
