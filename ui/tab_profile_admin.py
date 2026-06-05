"""Perfil de administrador: gestão de utilizadores e visão do sistema."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime

from nicegui import run, ui

from config.paths import DB_PATH, OUTPUT_DIR
from db.models import UserRole
from db.repository import UserRecord, UserRepository
from services.analytics import get_dashboard_stats
from ui.auth import session_email, session_name
from ui.components.user_admin_dialogs import (
    confirm_delete_user_dialog,
    open_manage_user_dialog,
)
from ui.components.user_create_panel import render_add_user_panel
from ui.pages.routes import ROUTE_PROFILE, ROUTE_SETTINGS
from ui.widgets import page_header

logger = logging.getLogger(__name__)


def _format_dt(value: datetime | None) -> str:
    if not value:
        return "—"
    if value.tzinfo:
        value = value.replace(tzinfo=None)
    return value.strftime("%d/%m/%Y %H:%M")


def _role_label(role: str) -> str:
    return "Administrador" if role == UserRole.ADMIN.value else "Utilizador"


def build_tab_profile_admin(config) -> None:
    """Painel administrativo (apenas para contas com papel admin)."""
    users_box = ui.element("div").classes("geo-admin-users w-full")
    stats_box = ui.element("div").classes("geo-admin-stats-grid w-full")

    page_header(
        "Administração",
        "Gerencie contas, papéis de acesso e acompanhe o uso do Content Studio.",
        eyebrow="Conta de administrador",
        actions=lambda: ui.button(
            "Meu perfil",
            icon="person",
            on_click=lambda: ui.navigate.to(ROUTE_PROFILE),
        ).props("flat dense no-caps color=primary"),
    )

    with ui.element("div").classes("geo-admin-page w-full"):
        with ui.element("div").classes(
            "geo-profile-account-card geo-profile-account-card--admin"
        ):
            with ui.row().classes("items-center gap-3 w-full"):
                with ui.element("div").classes(
                    "geo-profile-account-card__avatar geo-profile-account-card__avatar--admin"
                ):
                    ui.icon("admin_panel_settings")
                with ui.column().classes("gap-0 flex-grow min-w-0"):
                    ui.label(session_name() or "Administrador").classes(
                        "geo-profile-account-card__name"
                    )
                    ui.label(session_email() or "—").classes(
                        "geo-profile-account-card__email"
                    )
                    ui.html(
                        '<span class="geo-profile-role-badge geo-profile-role-badge--admin">'
                        "Administrador</span>"
                    )

        stats_box

        with ui.element("div").classes("geo-profile-layout geo-profile-layout--split"):
            with ui.element("div").classes("geo-profile-layout__main"):
                with ui.element("section").classes(
                    "geo-profile-section geo-admin-users-section"
                ):
                    with ui.row().classes(
                        "w-full items-center justify-between flex-wrap gap-2 mb-4"
                    ):
                        ui.label("Utilizadores registados").classes(
                            "geo-profile-section__title !mb-0"
                        )
                        ui.button(
                            "Configurações do sistema",
                            icon="settings",
                            on_click=lambda: ui.navigate.to(ROUTE_SETTINGS),
                        ).props("flat dense no-caps color=primary")

                    users_box

            with ui.element("aside").classes("geo-profile-layout__aside"):
                render_add_user_panel(
                    sidebar=True,
                    on_created=lambda: asyncio.create_task(refresh()),
                )

    def render_stats() -> None:
        stats = get_dashboard_stats()
        user_repo = UserRepository()
        total_users = user_repo.count_users()
        total_admins = user_repo.count_by_role(UserRole.ADMIN.value)

        stats_box.clear()
        with stats_box:
            _stat_card("Utilizadores", str(total_users), "group", "primary")
            _stat_card(
                "Administradores", str(total_admins), "shield_person", "secondary"
            )
            _stat_card(
                "Matérias no histórico",
                str(stats.get("total_articles", 0)),
                "article",
                "tertiary",
            )
            _stat_card(
                "Armazenamento (BD)",
                stats.get("storage_db_label", "0 B"),
                "database",
                "muted",
            )

    def render_users(records: list[UserRecord]) -> None:
        users_box.clear()
        with users_box:
            if not records:
                ui.label("Nenhum utilizador registado na base de dados.").classes(
                    "text-grey-7"
                )
                return

            with ui.element("div").classes("geo-admin-users-table"):
                for user in records:
                    is_self = user.email.lower() == session_email().lower()
                    row_cls = (
                        "geo-admin-user-row geo-admin-user-row--self"
                        if is_self
                        else "geo-admin-user-row"
                    )
                    articles = UserRepository().count_articles(user.id)

                    with ui.element("div").classes(row_cls):
                        with ui.column().classes("gap-0 min-w-0 flex-grow"):
                            with ui.row().classes("items-center gap-2 flex-wrap"):
                                ui.label(user.name or "—").classes(
                                    "geo-admin-user-row__name"
                                )
                                if is_self:
                                    ui.html(
                                        '<span class="geo-admin-you-chip">Você</span>'
                                    )
                                ui.html(
                                    f'<span class="geo-admin-role-chip geo-admin-role-chip--{user.role}">'
                                    f"{_role_label(user.role)}</span>"
                                )
                            ui.label(user.email).classes("geo-admin-user-row__meta")
                            ui.label(
                                f"Registo: {_format_dt(user.created_at)} · "
                                f"ID #{user.id} · {articles} matéria(s)"
                            ).classes("geo-admin-user-row__meta")

                        with ui.row().classes("geo-admin-user-actions gap-2 flex-shrink-0"):
                            ui.button(
                                "Gerenciar",
                                icon="manage_accounts",
                                on_click=lambda u=user: open_manage_user_dialog(
                                    u, on_saved=refresh
                                ),
                            ).props("outline dense no-caps color=primary")

                            delete_btn = ui.button(
                                "Excluir",
                                icon="delete",
                                on_click=lambda u=user: confirm_delete_user_dialog(
                                    u, on_deleted=refresh
                                ),
                            ).props("outline dense no-caps color=negative")
                            if is_self:
                                delete_btn.disable()
                                delete_btn.tooltip(
                                    "Não pode excluir a conta da sessão atual"
                                )

            with ui.element("div").classes("geo-admin-system-card mt-4"):
                ui.label("Sistema").classes("geo-profile-section__title")
                ui.label(f"Base de dados: {DB_PATH}").classes("geo-meta-caption")
                ui.label(f"Exportações: {OUTPUT_DIR}").classes("geo-meta-caption")

    async def refresh() -> None:
        try:
            records = await run.io_bound(UserRepository().list_all)
        except Exception as exc:
            logger.exception("Erro ao listar utilizadores: %s", exc)
            ui.notify(f"Erro ao carregar utilizadores: {exc}", type="negative")
            return
        render_stats()
        render_users(records)

    ui.timer(0.05, refresh, once=True)


def _stat_card(label: str, value: str, icon: str, tone: str) -> None:
    with ui.element("div").classes(f"geo-admin-stat-card geo-admin-stat-card--{tone}"):
        with ui.element("div").classes("geo-admin-stat-card__icon"):
            ui.icon(icon)
        ui.label(label).classes("geo-admin-stat-card__label")
        ui.label(value).classes("geo-admin-stat-card__value")
