"""Entrada do perfil: delega para utilizador comum ou administrador."""

from __future__ import annotations

from ui.tab_profile_user import build_tab_profile_user


def build_tab_profile(config) -> None:
    """Perfil pessoal (todas as contas, incluindo administradores)."""
    build_tab_profile_user(config)
