"""Definição central das rotas das páginas do Content Studio."""

from __future__ import annotations

ROUTE_HOME = "/"
ROUTE_LOGIN = "/login"
ROUTE_SIGNUP = "/cadastro"
ROUTE_DASHBOARD = "/dashboard"
ROUTE_BLOG = "/criar-materia"
ROUTE_URLS = "/urls"
ROUTE_TEXT = "/texto"
ROUTE_JSON = "/json"
ROUTE_BATCH = "/lote"
ROUTE_HISTORY = "/historico"
ROUTE_PROFILE = "/perfil"
ROUTE_ADMIN = "/admin"
ROUTE_SETTINGS = "/configuracoes"

# (path, rótulo, ícone) na ordem em que aparecem na barra lateral.
NAV_ITEMS: list[tuple[str, str, str]] = [
    (ROUTE_DASHBOARD, "Dashboard", "dashboard"),
    (ROUTE_BLOG, "Criar matéria", "edit_note"),
    (ROUTE_URLS, "URLs", "link"),
    (ROUTE_TEXT, "Texto manual", "description"),
    (ROUTE_JSON, "JSON ChatGPT", "data_object"),
    (ROUTE_BATCH, "Lote CSV", "table_chart"),
    (ROUTE_HISTORY, "Histórico", "history"),
    (ROUTE_PROFILE, "Perfil", "account_circle"),
    (ROUTE_SETTINGS, "Settings", "settings"),
]

ADMIN_NAV_ITEM: tuple[str, str, str] = (
    ROUTE_ADMIN,
    "Administração",
    "admin_panel_settings",
)


def nav_items_for_session() -> list[tuple[str, str, str]]:
    """Itens da sidebar conforme o papel da sessão atual."""
    from ui.auth import is_admin

    items = list(NAV_ITEMS)
    if is_admin():
        profile_idx = next(
            i for i, (_, label, _) in enumerate(items) if label == "Perfil"
        )
        items.insert(profile_idx + 1, ADMIN_NAV_ITEM)
    return items
