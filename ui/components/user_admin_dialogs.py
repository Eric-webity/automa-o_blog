"""Diálogos de gerir e excluir contas (admin)."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable

from nicegui import run, ui

from db.models import UserRole
from db.repository import UserRecord, UserRepository
from ui.auth import session_email

logger = logging.getLogger(__name__)

_ROLE_OPTIONS = {
    "Utilizador": UserRole.USER.value,
    "Administrador": UserRole.ADMIN.value,
}
_ROLE_LABELS = {v: k for k, v in _ROLE_OPTIONS.items()}


def _invoke_callback(callback: Callable[[], None] | Awaitable[None]) -> None:
    result = callback()
    if hasattr(result, "__await__"):
        asyncio.create_task(result)


def _role_badge_html(role: str) -> str:
    if role == UserRole.ADMIN.value:
        return (
            '<span class="geo-profile-role-badge geo-profile-role-badge--admin">'
            "Administrador</span>"
        )
    return (
        '<span class="geo-profile-role-badge geo-profile-role-badge--user">'
        "Utilizador</span>"
    )


def open_manage_user_dialog(
    user: UserRecord,
    *,
    on_saved: Callable[[], None] | Awaitable[None],
) -> None:
    """Abre formulário para editar conta."""
    article_count = UserRepository().count_articles(user.id)

    with ui.dialog() as dialog, ui.card().classes("geo-user-admin-dialog p-4"):
        ui.label("Gerenciar utilizador").classes("text-h6")
        ui.html(
            f'<p class="geo-page-desc !mt-0">ID #{user.id} · '
            f"{article_count} matéria(s) no histórico · {_role_badge_html(user.role)}</p>"
        )

        name_input = ui.input("Nome completo", value=user.name or "").props(
            "outlined dense"
        ).classes("w-full")
        email_input = ui.input("E-mail", value=user.email or "").props(
            "outlined dense type=email"
        ).classes("w-full")
        role_select = (
            ui.select(
                _ROLE_OPTIONS,
                label="Papel",
                value=_ROLE_LABELS.get(user.role, "Utilizador"),
            )
            .classes("w-full")
            .props("outlined dense")
        )
        password_input = ui.input(
            "Nova senha (opcional)",
            placeholder="Deixe vazio para manter a atual",
        ).props("outlined dense type=password").classes("w-full")

        def save() -> None:
            new_role = _ROLE_OPTIONS.get(role_select.value, UserRole.USER.value)
            try:
                UserRepository().update(
                    user.id,
                    name=name_input.value or "",
                    email=email_input.value or "",
                    role=new_role,
                    password=password_input.value or None,
                )
            except ValueError as exc:
                ui.notify(str(exc), type="warning")
                return
            except Exception as exc:
                logger.exception("Erro ao atualizar utilizador: %s", exc)
                ui.notify(f"Erro: {exc}", type="negative")
                return
            ui.notify(f"Conta {email_input.value} atualizada.", type="positive")
            dialog.close()
            _invoke_callback(on_saved)

        with ui.row().classes("w-full justify-end gap-2 mt-2"):
            ui.button("Cancelar", on_click=dialog.close).props("flat no-caps")
            ui.button("Guardar alterações", icon="save", on_click=save).props(
                "color=primary unelevated no-caps"
            )

    dialog.open()


def confirm_delete_user_dialog(
    user: UserRecord,
    *,
    on_deleted: Callable[[], None] | Awaitable[None],
) -> None:
    """Confirma exclusão permanente da conta."""
    is_self = user.email.lower() == session_email().lower()
    article_count = UserRepository().count_articles(user.id)

    with ui.dialog() as dialog, ui.card().classes("geo-user-admin-dialog p-4"):
        ui.label("Excluir utilizador").classes("text-h6 text-negative")
        if is_self:
            ui.label("Não pode excluir a conta com que está autenticado.").classes(
                "geo-page-desc text-orange-8"
            )
        else:
            ui.label(
                f"Tem a certeza que deseja excluir «{user.name or user.email}»? "
                f"Esta ação não pode ser desfeita."
            ).classes("geo-page-desc !mt-0")
            if article_count:
                ui.label(
                    f"As {article_count} matéria(s) desta conta permanecem no sistema "
                    "sem dono (podem ser reatribuídas manualmente na base de dados)."
                ).classes("geo-meta-caption text-orange-8")

        async def do_delete() -> None:
            if is_self:
                ui.notify("Não pode excluir a sua própria conta.", type="warning")
                return
            try:
                deleted = await run.io_bound(UserRepository().delete, user.id)
            except ValueError as exc:
                ui.notify(str(exc), type="warning")
                return
            except Exception as exc:
                logger.exception("Erro ao excluir utilizador id=%s: %s", user.id, exc)
                ui.notify(f"Erro: {exc}", type="negative")
                return
            if not deleted:
                ui.notify("Utilizador não encontrado.", type="warning")
                return
            ui.notify(f"Conta {user.email} removida.", type="positive")
            dialog.close()
            _invoke_callback(on_deleted)

        with ui.row().classes("w-full justify-end gap-2 mt-2"):
            ui.button("Cancelar", on_click=dialog.close).props("flat no-caps")
            ui.button(
                "Excluir",
                icon="delete",
                on_click=lambda: asyncio.create_task(do_delete()),
            ).props("color=negative unelevated no-caps").set_enabled(not is_self)

    dialog.open()
