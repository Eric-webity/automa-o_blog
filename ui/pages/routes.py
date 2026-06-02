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
ROUTE_HISTORY = "/historico"
ROUTE_PROFILE = "/perfil"
ROUTE_SETTINGS = "/configuracoes"

# (path, rótulo, ícone) na ordem em que aparecem na barra lateral.
NAV_ITEMS: list[tuple[str, str, str]] = [
    (ROUTE_DASHBOARD, "Dashboard", "dashboard"),
    (ROUTE_BLOG, "Criar matéria", "edit_note"),
    (ROUTE_URLS, "URLs", "link"),
    (ROUTE_TEXT, "Texto manual", "description"),
    (ROUTE_JSON, "JSON ChatGPT", "data_object"),
    (ROUTE_HISTORY, "Histórico", "history"),
    (ROUTE_PROFILE, "Perfil", "account_circle"),
    (ROUTE_SETTINGS, "Settings", "settings"),
]
