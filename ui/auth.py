"""Autenticação local da UI (sessão NiceGUI)."""

from __future__ import annotations

import os

from nicegui import app

from db.models import UserRole
from db.user_scope import ensure_user_id_for_email
from db.repository import BlogProfileRecord, BlogProfileRepository, UserRepository


def is_authenticated() -> bool:
    return bool(app.storage.user.get("authenticated"))


def session_email() -> str:
    return str(app.storage.user.get("email") or "")


def session_name() -> str:
    return str(app.storage.user.get("name") or "")


def session_role() -> str:
    return str(app.storage.user.get("role") or UserRole.USER.value)


def session_user_id() -> int | None:
    raw = app.storage.user.get("user_id")
    if raw is None:
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def require_session_user_id() -> int:
    """Id do utilizador autenticado (obrigatório para histórico e gravações)."""
    user_id = session_user_id()
    if user_id is not None:
        return user_id
    email = session_email()
    if email:
        user_id = ensure_user_id_for_email(email, name=session_name())
        app.storage.user["user_id"] = user_id
        return user_id
    raise RuntimeError("Sessão sem utilizador autenticado.")


def article_repository():
    """Repositório de matérias limitado à conta da sessão."""
    from db.repository import ArticleRepository

    return ArticleRepository(user_id=require_session_user_id())


def is_admin() -> bool:
    return session_role() == UserRole.ADMIN.value


def _admin_email_from_env() -> str:
    return (
        os.getenv("GEO_ADMIN_EMAIL", "").strip().lower()
        or os.getenv("GEO_LOGIN_EMAIL", "").strip().lower()
    )


def resolve_role_for_email(email: str) -> str:
    """Obtém o papel a partir da base de dados ou das credenciais de ambiente."""
    normalized = email.strip().lower()
    user = UserRepository().get_by_email(normalized)
    if user:
        return user.role
    if _admin_email_from_env() and normalized == _admin_email_from_env():
        return UserRole.ADMIN.value
    return UserRole.USER.value


def _set_session(
    *,
    email: str,
    name: str = "",
    role: str | None = None,
    user_id: int | None = None,
) -> None:
    normalized = email.strip().lower()
    app.storage.user["authenticated"] = True
    app.storage.user["email"] = normalized
    app.storage.user["name"] = name.strip()
    app.storage.user["role"] = role or resolve_role_for_email(normalized)
    resolved_id = user_id
    if resolved_id is None:
        user = UserRepository().get_by_email(normalized)
        if user:
            resolved_id = user.id
    if resolved_id is None:
        resolved_id = ensure_user_id_for_email(normalized, name=name)
    app.storage.user["user_id"] = resolved_id


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
    _set_session(email=user.email, name=user.name, role=user.role, user_id=user.id)
    return True, "registered"


def authenticate(email: str, password: str) -> tuple[bool, str]:
    """Valida credenciais e grava sessão do browser."""
    email = (email or "").strip()
    password = password or ""

    if not email or not password:
        return False, "Preencha e-mail e senha."

    user = UserRepository().verify_credentials(email, password)
    if user:
        _set_session(email=user.email, name=user.name, role=user.role, user_id=user.id)
        return True, "ok"

    expected_email = os.getenv("GEO_LOGIN_EMAIL", "").strip()
    expected_password = os.getenv("GEO_LOGIN_PASSWORD", "").strip()

    if expected_email and expected_password:
        if email.lower() != expected_email.lower() or password != expected_password:
            return False, "E-mail ou senha incorretos."
    elif "@" not in email or len(password) < 4:
        return False, "E-mail ou senha incorretos."

    _set_session(email=email, name=email.split("@")[0])
    return True, "ok"


def logout() -> None:
    app.storage.user.clear()
