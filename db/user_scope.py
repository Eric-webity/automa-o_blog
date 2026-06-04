"""Resolução de utilizador para escopo de matérias (UI, API, serviços)."""

from __future__ import annotations

import os
import secrets

from db.repository import UserRepository


def ensure_user_id_for_email(email: str, *, name: str = "") -> int:
    """Garante registo em ``users`` e devolve o id (login por ambiente incluído)."""
    normalized = email.strip().lower()
    if not normalized:
        raise ValueError("E-mail inválido para associar matérias.")

    repo = UserRepository()
    existing = repo.get_by_email(normalized)
    if existing:
        return existing.id

    display = (name or normalized.split("@")[0] or "Utilizador").strip()[:200]
    created = repo.create(
        name=display,
        email=normalized,
        password=secrets.token_urlsafe(24),
    )
    return created.id


def resolve_api_owner_user_id() -> int | None:
    """
    Utilizador dono das matérias criadas/listadas via API REST.

    Ordem: GEO_API_OWNER_EMAIL → GEO_LOGIN_EMAIL → primeiro utilizador na base.
    """
    for key in ("GEO_API_OWNER_EMAIL", "GEO_LOGIN_EMAIL"):
        email = os.getenv(key, "").strip()
        if email:
            return ensure_user_id_for_email(email)

    repo = UserRepository()
    users = repo.list_all(limit=1)
    return users[0].id if users else None
