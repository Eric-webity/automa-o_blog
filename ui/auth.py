"""Autenticação local da UI (sessão NiceGUI)."""

from __future__ import annotations

import os

from nicegui import app

from db.repository import BlogProfileRecord, BlogProfileRepository, UserRepository


def is_authenticated() -> bool:
    return bool(app.storage.user.get("authenticated"))


def session_email() -> str:
    return str(app.storage.user.get("email") or "")


def session_name() -> str:
    return str(app.storage.user.get("name") or "")


def _set_session(*, email: str, name: str = "") -> None:
    app.storage.user["authenticated"] = True
    app.storage.user["email"] = email.strip().lower()
    app.storage.user["name"] = name.strip()


def _sync_profile(name: str, email: str) -> None:
    """Preenche perfil do blog com dados do cadastro quando ainda vazio."""
    repo = BlogProfileRepository()
    profile = repo.get_profile()
    if profile is None:
        repo.save_profile(
            BlogProfileRecord(
                id=None,
                name=name,
                email=email,
                phone="",
                bio="",
                title="",
                description="",
            )
        )
        return
    if not profile.name.strip() or not profile.email.strip():
        repo.save_profile(
            BlogProfileRecord(
                id=profile.id,
                name=profile.name.strip() or name,
                email=profile.email.strip() or email,
                phone=profile.phone,
                bio=profile.bio,
                title=profile.title,
                description=profile.description,
            )
        )


def register_user(
    name: str,
    email: str,
    password: str,
    confirm_password: str,
    *,
    accepted_terms: bool,
) -> tuple[bool, str]:
    name = (name or "").strip()
    email = (email or "").strip().lower()
    password = password or ""
    confirm_password = confirm_password or ""

    if not name:
        return False, "Informe seu nome completo."
    if "@" not in email:
        return False, "Informe um e-mail válido."
    if len(password) < 8:
        return False, "A senha deve ter pelo menos 8 caracteres."
    if password != confirm_password:
        return False, "As senhas não coincidem."
    if not accepted_terms:
        return False, "Aceite os Termos de Serviço para continuar."

    try:
        user = UserRepository().create(name=name, email=email, password=password)
    except ValueError as exc:
        return False, str(exc)

    _sync_profile(user.name, user.email)
    _set_session(email=user.email, name=user.name)
    return True, ""


def authenticate(email: str, password: str) -> tuple[bool, str]:
    """Valida credenciais e grava sessão do browser."""
    email = (email or "").strip()
    password = password or ""

    if not email or not password:
        return False, "Preencha e-mail e senha."

    user = UserRepository().verify_credentials(email, password)
    if user:
        _set_session(email=user.email, name=user.name)
        return True, ""

    expected_email = os.getenv("GEO_LOGIN_EMAIL", "").strip()
    expected_password = os.getenv("GEO_LOGIN_PASSWORD", "").strip()

    if expected_email and expected_password:
        if email.lower() != expected_email.lower() or password != expected_password:
            return False, "E-mail ou senha incorretos."
    elif "@" not in email or len(password) < 4:
        return False, "E-mail ou senha incorretos."

    _set_session(email=email)
    return True, ""


def logout() -> None:
    app.storage.user.clear()
