"""Perfil do utilizador comum: dados pessoais e blog local."""

from __future__ import annotations

import logging

from nicegui import ui

from db.repository import BlogProfileRecord, BlogProfileRepository
from ui.auth import is_admin, session_email, session_name
from ui.pages.routes import ROUTE_ADMIN
from ui.widgets import geo_input, geo_textarea, page_header

logger = logging.getLogger(__name__)


def _field(record: BlogProfileRecord | None, attr: str) -> str:
    if record is None:
        return ""
    return getattr(record, attr, "") or ""


def build_tab_profile_user(config) -> None:
    """Formulário de perfil para contas de utilizador."""
    page_header(
        "Meu perfil",
        "Atualize os seus dados pessoais e as informações públicas do blog.",
        eyebrow="Conta de utilizador",
    )

    repo = BlogProfileRepository()
    record = repo.get_profile()
    display_name = _field(record, "name") or session_name()
    display_email = _field(record, "email") or session_email()

    with ui.element("div").classes("geo-profile-page w-full"):
        with ui.element("div").classes("geo-profile-account-card"):
            with ui.row().classes("items-center gap-3 w-full"):
                with ui.element("div").classes("geo-profile-account-card__avatar"):
                    ui.icon("person")
                with ui.column().classes("gap-0 flex-grow min-w-0"):
                    ui.label(display_name or "Utilizador").classes(
                        "geo-profile-account-card__name"
                    )
                    ui.label(display_email or "—").classes("geo-profile-account-card__email")
                    ui.html(
                        '<span class="geo-profile-role-badge geo-profile-role-badge--user">'
                        "Utilizador</span>"
                    )
            if is_admin():
                ui.button(
                    "Abrir painel de administração",
                    icon="admin_panel_settings",
                    on_click=lambda: ui.navigate.to(ROUTE_ADMIN),
                ).props("outline color=primary no-caps").classes("self-start mt-3")

        with ui.element("section").classes("geo-profile-section"):
            ui.label("Dados pessoais").classes("geo-profile-section__title")
            name_input = geo_input("Nome completo", value=_field(record, "name") or display_name)
            email_input = geo_input(
                "E-mail",
                value=display_email,
                placeholder="seu@email.com",
            )
            phone_input = geo_input(
                "Telefone (opcional)",
                value=_field(record, "phone"),
                placeholder="+55 11 91234-5678",
            )
            bio_input = geo_textarea(
                "Biografia / apresentação (opcional)",
                value=_field(record, "bio"),
                rows=4,
                placeholder="Breve descrição sobre si ou a sua marca.",
            )

        with ui.element("section").classes("geo-profile-section"):
            ui.label("Blog local").classes("geo-profile-section__title")
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
                ui.notify("Indique um e-mail válido.", color="orange")
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
            try:
                repo.save_profile(new_record)
            except Exception as exc:
                logger.exception("Falha ao salvar perfil: %s", exc)
                ui.notify(f"Erro ao salvar perfil: {exc}", type="negative")
                return
            ui.notify("Perfil salvo com sucesso!", type="positive")

        ui.button("Salvar perfil", icon="save", on_click=save_profile).props(
            "color=primary unelevated"
        ).classes("geo-profile-save-btn self-end")
