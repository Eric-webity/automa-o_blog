"""Estado da UI ligado à conta autenticada (vários logins na mesma máquina)."""

from __future__ import annotations

from nicegui import ui

from ui.auth import require_session_user_id, session_email, session_name


def sync_config_session(config) -> int:
    """Atualiza ``config.session_user_id`` com o utilizador da sessão NiceGUI."""
    user_id = require_session_user_id()
    config.session_user_id = user_id
    return user_id


def account_label() -> str:
    """Rótulo curto da conta ativa (e-mail ou nome)."""
    return session_email() or session_name() or "Conta"


def account_scope_caption() -> str:
    """Texto para cabeçalhos de histórico/dashboard."""
    email = session_email()
    if email:
        return (
            f"Conta ativa: {email}. O histórico, o dashboard e as gravações "
            "mostram apenas as matérias desta conta."
        )
    return "As matérias guardadas pertencem apenas à conta com que entrou."


def notify_login_scope(*, is_new_registration: bool = False) -> None:
    """Aviso após login — dados isolados por utilizador."""
    label = account_label()
    prefix = "Conta criada" if is_new_registration else "Sessão iniciada"
    ui.notify(
        f"{prefix} como {label}. O histórico e as estatísticas são só desta conta.",
        type="positive",
        timeout=6000,
    )


def reset_owned_tab_state(state: dict, *, user_id: int) -> None:
    """
    Limpa IDs em memória quando outro utilizador entra na mesma sessão do browser.

    Evita reutilizar ``article_id`` de uma conta anterior ao guardar/regenerar.
    """
    if state.get("owner_id") == user_id:
        return
    state["owner_id"] = user_id
    state["article_id"] = None
    if "id" in state:
        state["id"] = None
    state.pop("markdown", None)
    state.pop("editor", None)
    state.pop("preview", None)
    if "checklist" in state:
        state["checklist"] = {"manual": {}, "complete": False}
    if "meta" in state:
        state["meta"] = {}
