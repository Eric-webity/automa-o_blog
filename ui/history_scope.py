"""Escopo da aba Histórico: conta da sessão ou visão admin por utilizador."""

from __future__ import annotations

from db.models import ArticleStatus, UserRole
from db.repository import ArticleRecord, ArticleRepository, UserRecord, UserRepository

# Sentinel: administrador a ver todas as contas (não confundir com user_id real).
HISTORY_SCOPE_ALL: None = None

HISTORY_SCOPE_ALL_LABEL = "Todas as contas"


def user_display_name(user: UserRecord) -> str:
    """Nome apresentado no histórico (preferência: nome da conta)."""
    return (user.name or user.email or "").strip() or f"Conta #{user.id}"


def scope_option_label(user: UserRecord, *, article_count: int) -> str:
    """Rótulo do filtro admin: nome + contagem de matérias."""
    suffix = f" · {article_count} matéria(s)" if article_count else ""
    return f"{user_display_name(user)}{suffix}"


def build_scope_select_options() -> dict[str, int | None]:
    """Rótulo do select → id da conta (``None`` = todas; só para admin)."""
    repo_users = UserRepository()
    options: dict[str, int | None] = {HISTORY_SCOPE_ALL_LABEL: HISTORY_SCOPE_ALL}
    for user in repo_users.list_all():
        count = repo_users.count_articles(user.id)
        options[scope_option_label(user, article_count=count)] = user.id
    return options


def scope_label_for_id(scope_id: int | None, options: dict[str, int | None]) -> str:
    for label, uid in options.items():
        if uid == scope_id:
            return label
    return HISTORY_SCOPE_ALL_LABEL


def admin_owner_ids() -> set[int]:
    return {u.id for u in UserRepository().list_all() if u.role == UserRole.ADMIN.value}


def load_user_name_labels() -> dict[int, str]:
    return {u.id: user_display_name(u) for u in UserRepository().list_all()}


def sort_history_records(records: list[ArticleRecord]) -> list[ArticleRecord]:
    """Rascunhos primeiro; depois mais recentes."""

    def _sort_key(record: ArticleRecord) -> tuple[int, float]:
        draft_first = 0 if record.status == ArticleStatus.DRAFT.value else 1
        created = record.created_at.timestamp() if record.created_at else 0.0
        return (draft_first, -created)

    return sorted(records, key=_sort_key)


def filter_drafts_only(records: list[ArticleRecord], *, enabled: bool) -> list[ArticleRecord]:
    if not enabled:
        return records
    return [r for r in records if r.status == ArticleStatus.DRAFT.value]


def count_drafts(by_status: dict[str, int] | None) -> int:
    if not by_status:
        return 0
    return int(by_status.get(ArticleStatus.DRAFT.value, 0))


def resolve_user_by_name(name: str) -> tuple[UserRecord | None, str | None]:
    """Resolve utilizador pelo nome (sem distinção de maiúsculas)."""
    needle = (name or "").strip().lower()
    if not needle:
        return None, "Indique o nome do utilizador."
    matches = [
        u
        for u in UserRepository().list_all()
        if user_display_name(u).lower() == needle or u.name.strip().lower() == needle
    ]
    if not matches:
        return None, f"Utilizador «{name.strip()}» não encontrado."
    if len(matches) > 1:
        return None, "Vários utilizadores com este nome; use o e-mail no Perfil."
    return matches[0], None


def filter_visible_records(
    records: list[ArticleRecord],
    *,
    session_user_id: int,
    is_admin: bool,
) -> list[ArticleRecord]:
    """Utilizador comum não vê matérias de contas administrador."""
    if is_admin:
        return records
    blocked = admin_owner_ids() - {session_user_id}
    if not blocked:
        return records
    return [r for r in records if r.user_id not in blocked]


def record_accessible(
    record: ArticleRecord | None,
    *,
    session_user_id: int,
    is_admin: bool,
) -> bool:
    if record is None:
        return False
    if is_admin:
        return True
    if record.user_id == session_user_id:
        return True
    if record.user_id in admin_owner_ids():
        return False
    return record.user_id == session_user_id


def history_mutate_owner_id(
    record: ArticleRecord,
    *,
    session_user_id: int,
    is_admin: bool,
    scope_user_id: int | None,
) -> tuple[int | None, str | None]:
    """Dono para atualizar/aprovar matéria; recusa acesso indevido."""
    if not record_accessible(
        record,
        session_user_id=session_user_id,
        is_admin=is_admin,
    ):
        return None, "Sem permissão para alterar esta matéria."
    owner = history_write_user_id(
        session_user_id=session_user_id,
        is_admin=is_admin,
        scope_user_id=scope_user_id,
        record=record,
    )
    if record.user_id is not None and owner != record.user_id:
        return None, "A matéria pertence a outra conta."
    return owner, None


def history_list_repository(
    *,
    session_user_id: int,
    is_admin: bool,
    scope_user_id: int | None,
) -> ArticleRepository:
    """Repositório para listar/abrir/apagar matérias conforme o filtro ativo."""
    if not is_admin:
        return ArticleRepository(user_id=session_user_id)
    if scope_user_id is HISTORY_SCOPE_ALL:
        return ArticleRepository()
    if isinstance(scope_user_id, int):
        return ArticleRepository(user_id=scope_user_id)
    return ArticleRepository(user_id=session_user_id)


def history_list_records(
    *,
    session_user_id: int,
    is_admin: bool,
    scope_user_id: int | None,
    limit: int = 200,
) -> list[ArticleRecord]:
    records = history_list_repository(
        session_user_id=session_user_id,
        is_admin=is_admin,
        scope_user_id=scope_user_id,
    ).list_all(limit=limit)
    return filter_visible_records(
        records,
        session_user_id=session_user_id,
        is_admin=is_admin,
    )


def history_write_user_id(
    *,
    session_user_id: int,
    is_admin: bool,
    scope_user_id: int | None,
    record: ArticleRecord | None = None,
) -> int:
    """Dono da matéria em gravações (rascunho, aprovar) — respeita filtro admin."""
    if not is_admin:
        return session_user_id
    if isinstance(scope_user_id, int):
        return scope_user_id
    if record is not None and record.user_id is not None:
        return record.user_id
    return session_user_id


def history_import_owner_id(
    *,
    is_admin: bool,
    scope_user_id: int | None,
    session_user_id: int,
    import_username: str = "",
) -> tuple[int | None, str | None]:
    """Destino da importação: nome do utilizador (admin) ou conta da sessão."""
    if not is_admin:
        return session_user_id, None
    name = (import_username or "").strip()
    if name:
        user, err = resolve_user_by_name(name)
        if err or user is None:
            return None, err
        return user.id, None
    if scope_user_id is HISTORY_SCOPE_ALL:
        return None, "Indique o nome do utilizador para importar a matéria."
    if isinstance(scope_user_id, int):
        return scope_user_id, None
    return session_user_id, None


def history_stats_user_id(
    *,
    session_user_id: int,
    is_admin: bool,
    scope_user_id: int | None,
) -> int | None:
    """``user_id`` para métricas; ``None`` = totais do sistema (admin, todas)."""
    if not is_admin:
        return session_user_id
    if scope_user_id is HISTORY_SCOPE_ALL:
        return None
    if isinstance(scope_user_id, int):
        return scope_user_id
    return session_user_id


def history_page_caption(
    *,
    is_admin: bool,
    scope_user_id: int | None,
    session_email: str,
    filtered_name: str | None = None,
) -> str:
    if not is_admin:
        if session_email:
            return (
                f"Conta ativa: {session_email}. Só vê o seu histórico — "
                "matérias de administradores não são visíveis."
            )
        return (
            "O histórico é privado: apenas as suas matérias, "
            "sem acesso a contas de administrador."
        )
    if scope_user_id is HISTORY_SCOPE_ALL:
        return (
            "Visão de administrador: histórico de todas as contas. "
            "Filtre pelo nome do utilizador ou importe indicando o nome no formulário."
        )
    if filtered_name:
        return (
            f"Administrador a ver o histórico de {filtered_name}. "
            "Importações para esta conta podem usar o mesmo nome no diálogo."
        )
    return "Histórico filtrado por nome de utilizador."
