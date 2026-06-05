"""Formulário reutilizável para criar conta local (admin)."""

from __future__ import annotations

from collections.abc import Callable

from nicegui import ui

from db.models import UserRole
from ui.auth import admin_create_user


def render_add_user_panel(
    *,
    on_created: Callable[[], None] | None = None,
    sidebar: bool = False,
) -> None:
    """Secção «Adicionar pessoa» com nome, e-mail, senha e papel."""
    role_options = {
        "Utilizador": UserRole.USER.value,
        "Administrador": UserRole.ADMIN.value,
    }

    section_cls = "geo-profile-section geo-add-user-section"
    if sidebar:
        section_cls += " geo-add-user-sidebar"

    with ui.element("section").classes(section_cls):
        ui.label("Adicionar nova pessoa").classes("geo-profile-section__title")
        ui.label(
            "Crie uma conta local para outro membro da equipa. "
            "O histórico e as matérias ficam isolados por login."
        ).classes("geo-page-desc !mt-0 mb-4")

        name_input = ui.input("Nome completo", placeholder="Nome da pessoa").props(
            "outlined dense"
        ).classes("w-full")
        email_input = ui.input("E-mail", placeholder="email@empresa.com").props(
            "outlined dense type=email"
        ).classes("w-full")
        password_input = ui.input("Senha inicial", placeholder="Mínimo 8 caracteres").props(
            "outlined dense type=password"
        ).classes("w-full")
        role_select = ui.select(
            role_options,
            label="Papel",
            value="Utilizador",
        ).classes("w-full").props("outlined dense")

        def submit() -> None:
            ok, message = admin_create_user(
                name_input.value or "",
                email_input.value or "",
                password_input.value or "",
                role_options.get(role_select.value, UserRole.USER.value),
            )
            if not ok:
                ui.notify(message, type="warning")
                return
            ui.notify(message, type="positive")
            name_input.value = ""
            email_input.value = ""
            password_input.value = ""
            role_select.value = "Utilizador"
            if on_created:
                on_created()

        ui.button("Criar conta", icon="person_add", on_click=submit).props(
            "color=primary unelevated no-caps"
        ).classes("geo-profile-save-btn self-start mt-2")
