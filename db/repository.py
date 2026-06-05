"""Repositório de matérias no blog local (Content Studio)."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from core.passwords import hash_password, verify_password
from db.database import session_scope
from db.models import AiUsageLog, Article, ArticleStatus, BlogProfile, User, UserRole

logger = logging.getLogger(__name__)


@dataclass
class ArticleRecord:
    """DTO de matéria para a camada de UI."""

    id: int
    title: str
    markdown_content: str
    json_index: dict | None
    status: str
    created_at: datetime
    user_id: int | None = None


def _to_record(article: Article) -> ArticleRecord:
    """Converte linha ORM em DTO."""
    index_data: dict | None = None
    if article.json_index:
        try:
            index_data = json.loads(article.json_index)
        except json.JSONDecodeError:
            logger.warning("json_index inválido para artigo id=%s", article.id)
    return ArticleRecord(
        id=article.id,
        title=article.title,
        markdown_content=article.markdown_content,
        json_index=index_data,
        status=article.status,
        created_at=article.created_at,
        user_id=article.user_id,
    )


class ArticleRepository:
    """CRUD de matérias do blog local (opcionalmente filtrado por ``user_id``)."""

    def __init__(self, user_id: int | None = None) -> None:
        self._user_id = user_id

    def _owns(self, row: Article | None) -> bool:
        if row is None:
            return False
        if self._user_id is None:
            return True
        return row.user_id == self._user_id

    def _require_owner_id(self, user_id: int | None = None) -> int:
        owner = user_id if user_id is not None else self._user_id
        if owner is None:
            raise ValueError("user_id é obrigatório para gravar matérias.")
        return owner

    def create(
        self,
        *,
        title: str,
        markdown_content: str,
        json_index: dict | None = None,
        status: str = ArticleStatus.COMPLETED.value,
        user_id: int | None = None,
        session: Session | None = None,
    ) -> ArticleRecord:
        """Persiste uma nova matéria."""
        owner_id = self._require_owner_id(user_id)
        payload = json.dumps(json_index, ensure_ascii=False) if json_index else None
        article = Article(
            user_id=owner_id,
            title=title[:500],
            markdown_content=markdown_content,
            json_index=payload,
            status=status,
        )
        if session is not None:
            session.add(article)
            session.flush()
            session.refresh(article)
            return _to_record(article)

        with session_scope() as scoped:
            scoped.add(article)
            scoped.flush()
            scoped.refresh(article)
            return _to_record(article)

    def update(
        self,
        article_id: int,
        *,
        title: str | None = None,
        markdown_content: str | None = None,
        json_index: dict | None = None,
        status: str | None = None,
    ) -> ArticleRecord | None:
        """Atualiza matéria existente no blog local."""
        with session_scope() as session:
            row = session.get(Article, article_id)
            if not self._owns(row):
                return None
            if title is not None:
                row.title = title[:500]
            if markdown_content is not None:
                row.markdown_content = markdown_content
            if json_index is not None:
                row.json_index = json.dumps(json_index, ensure_ascii=False)
            if status is not None:
                row.status = status
            session.flush()
            session.refresh(row)
            return _to_record(row)

    def _article_query(self):
        stmt = select(Article)
        if self._user_id is not None:
            stmt = stmt.where(Article.user_id == self._user_id)
        return stmt

    def list_all(self, limit: int = 200) -> list[ArticleRecord]:
        """Lista matérias mais recentes primeiro."""
        with session_scope() as session:
            rows = session.scalars(
                self._article_query().order_by(Article.created_at.desc()).limit(limit)
            ).all()
            return [_to_record(row) for row in rows]

    def get_by_id(self, article_id: int) -> ArticleRecord | None:
        """Busca matéria por identificador."""
        with session_scope() as session:
            row = session.get(Article, article_id)
            return _to_record(row) if self._owns(row) else None

    def delete(self, article_id: int) -> bool:
        """Remove matéria do histórico."""
        with session_scope() as session:
            row = session.get(Article, article_id)
            if not self._owns(row):
                return False
            session.delete(row)
            return True

    def count_stats(self) -> dict[str, int | float | dict[str, int]]:
        """Agrega métricas para dashboard e API."""
        with session_scope() as session:
            base = select(func.count(Article.id))
            if self._user_id is not None:
                base = base.where(Article.user_id == self._user_id)
            total = int(session.scalar(base) or 0)
            status_stmt = select(Article.status, Article.markdown_content)
            if self._user_id is not None:
                status_stmt = status_stmt.where(Article.user_id == self._user_id)
            rows = session.execute(status_stmt).all()
        by_status: dict[str, int] = {}
        word_total = 0
        for status_val, content in rows:
            by_status[status_val] = by_status.get(status_val, 0) + 1
            word_total += len((content or "").split())
        avg_words = int(word_total / total) if total else 0
        return {
            "total": total,
            "avg_word_count": avg_words,
            "by_status": by_status,
        }

    def list_recent(self, limit: int = 5) -> list[ArticleRecord]:
        """Retorna as matérias mais recentes."""
        return self.list_all(limit=limit)

    def count_llm_articles(self) -> int:
        """Conta matérias geradas com IA (metadados em json_index)."""
        with session_scope() as session:
            index_stmt = select(Article.json_index)
            if self._user_id is not None:
                index_stmt = index_stmt.where(Article.user_id == self._user_id)
            rows = session.scalars(index_stmt).all()
        count = 0
        for raw in rows:
            if not raw:
                continue
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if not isinstance(data, dict):
                continue
            if data.get("used_llm") is True:
                count += 1
                continue
            mode = str(data.get("generation_mode", "")).strip().lower()
            if mode and mode != "local":
                count += 1
        return count

    def count_since_days(self, days: int = 7) -> int:
        """Conta matérias criadas nos últimos N dias."""
        from datetime import timedelta

        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        with session_scope() as session:
            stmt = select(func.count(Article.id)).where(Article.created_at >= cutoff)
            if self._user_id is not None:
                stmt = stmt.where(Article.user_id == self._user_id)
            count = session.scalar(stmt)
            return int(count or 0)


@dataclass
class BlogProfileRecord:
    """DTO do perfil (dados pessoais + blog local)."""

    id: int | None
    name: str
    email: str
    phone: str
    bio: str
    title: str
    description: str


def _to_profile_record(row: BlogProfile) -> BlogProfileRecord:
    return BlogProfileRecord(
        id=row.id,
        name=row.name,
        email=row.email,
        phone=row.phone,
        bio=row.bio,
        title=row.title,
        description=row.description,
    )


class BlogProfileRepository:
    """Persistência do perfil do blog (registo único)."""

    def get_profile(self) -> BlogProfileRecord | None:
        """Retorna o perfil salvo ou None se ainda não existir."""
        with session_scope() as session:
            row = session.scalars(select(BlogProfile).order_by(BlogProfile.id).limit(1)).first()
            return _to_profile_record(row) if row else None

    def save_profile(self, record: BlogProfileRecord) -> BlogProfileRecord:
        """Cria ou atualiza o perfil do blog."""
        with session_scope() as session:
            row: BlogProfile | None = None
            if record.id is not None:
                row = session.get(BlogProfile, record.id)
            if row is None:
                row = session.scalars(
                    select(BlogProfile).order_by(BlogProfile.id).limit(1)
                ).first()
            name = (record.name or "").strip()[:200]
            email = (record.email or "").strip()[:320]
            phone = (record.phone or "").strip()[:50]
            bio = (record.bio or "").strip()
            title = (record.title or "").strip()[:500]
            description = (record.description or "").strip()
            if row is None:
                row = BlogProfile(
                    name=name,
                    email=email,
                    phone=phone,
                    bio=bio,
                    title=title,
                    description=description,
                )
                session.add(row)
            else:
                row.name = name
                row.email = email
                row.phone = phone
                row.bio = bio
                row.title = title
                row.description = description
            session.flush()
            session.refresh(row)
            return _to_profile_record(row)


@dataclass
class UserRecord:
    """DTO de utilizador registado."""

    id: int
    name: str
    email: str
    role: str = UserRole.USER.value
    created_at: datetime | None = None


def _to_user_record(row: User) -> UserRecord:
    role = (row.role or UserRole.USER.value).strip().lower()
    if role not in {UserRole.USER.value, UserRole.ADMIN.value}:
        role = UserRole.USER.value
    return UserRecord(
        id=row.id,
        name=row.name,
        email=row.email,
        role=role,
        created_at=row.created_at,
    )


class UserRepository:
    """Registo e autenticação de contas locais."""

    def get_by_email(self, email: str) -> UserRecord | None:
        normalized = email.strip().lower()
        with session_scope() as session:
            row = session.scalars(
                select(User).where(func.lower(User.email) == normalized).limit(1)
            ).first()
            return _to_user_record(row) if row else None

    def get_by_id(self, user_id: int) -> UserRecord | None:
        with session_scope() as session:
            row = session.get(User, user_id)
            return _to_user_record(row) if row else None

    def email_exists(self, email: str) -> bool:
        return self.get_by_email(email) is not None

    def count_users(self) -> int:
        with session_scope() as session:
            return int(session.scalar(select(func.count(User.id))) or 0)

    def count_by_role(self, role: str) -> int:
        with session_scope() as session:
            return int(
                session.scalar(
                    select(func.count(User.id)).where(User.role == role)
                )
                or 0
            )

    def list_all(self, limit: int = 200) -> list[UserRecord]:
        with session_scope() as session:
            rows = session.scalars(
                select(User).order_by(User.created_at.desc()).limit(limit)
            ).all()
            return [_to_user_record(row) for row in rows]

    def create(
        self,
        *,
        name: str,
        email: str,
        password: str,
        role: str | None = None,
    ) -> UserRecord:
        normalized_email = email.strip().lower()
        display_name = name.strip()[:200]
        with session_scope() as session:
            existing = session.scalars(
                select(User).where(func.lower(User.email) == normalized_email).limit(1)
            ).first()
            if existing:
                raise ValueError("Este e-mail já está cadastrado.")
            user_count = int(session.scalar(select(func.count(User.id))) or 0)
            if role is None:
                role = UserRole.ADMIN.value if user_count == 0 else UserRole.USER.value
            else:
                role = role.strip().lower()
                if role not in {UserRole.USER.value, UserRole.ADMIN.value}:
                    raise ValueError("Papel inválido.")
            row = User(
                name=display_name,
                email=normalized_email,
                password_hash=hash_password(password),
                role=role,
            )
            session.add(row)
            session.flush()
            session.refresh(row)
            return _to_user_record(row)

    def verify_credentials(self, email: str, password: str) -> UserRecord | None:
        normalized = email.strip().lower()
        with session_scope() as session:
            row = session.scalars(
                select(User).where(func.lower(User.email) == normalized).limit(1)
            ).first()
            if not row or not verify_password(password, row.password_hash):
                return None
            return _to_user_record(row)

    def count_articles(self, user_id: int) -> int:
        """Número de matérias associadas ao utilizador."""
        with session_scope() as session:
            return int(
                session.scalar(
                    select(func.count(Article.id)).where(Article.user_id == user_id)
                )
                or 0
            )

    def _ensure_not_last_admin_demotion(
        self, session: Session, row: User, new_role: str
    ) -> None:
        if row.role == UserRole.ADMIN.value and new_role == UserRole.USER.value:
            admins = int(
                session.scalar(
                    select(func.count(User.id)).where(User.role == UserRole.ADMIN.value)
                )
                or 0
            )
            if admins <= 1:
                raise ValueError("Não é possível remover o último administrador.")

    def set_role(self, user_id: int, role: str) -> UserRecord:
        """Atualiza o papel de um utilizador (``user`` ou ``admin``)."""
        role = role.strip().lower()
        if role not in {UserRole.USER.value, UserRole.ADMIN.value}:
            raise ValueError("Papel inválido.")
        with session_scope() as session:
            row = session.get(User, user_id)
            if not row:
                raise ValueError("Utilizador não encontrado.")
            self._ensure_not_last_admin_demotion(session, row, role)
            row.role = role
            session.flush()
            session.refresh(row)
            return _to_user_record(row)

    def update(
        self,
        user_id: int,
        *,
        name: str,
        email: str,
        role: str,
        password: str | None = None,
    ) -> UserRecord:
        """Atualiza nome, e-mail, papel e opcionalmente a senha."""
        display_name = (name or "").strip()[:200]
        normalized_email = (email or "").strip().lower()
        if not display_name:
            raise ValueError("Informe o nome completo.")
        if "@" not in normalized_email:
            raise ValueError("Informe um e-mail válido.")
        role = (role or UserRole.USER.value).strip().lower()
        if role not in {UserRole.USER.value, UserRole.ADMIN.value}:
            raise ValueError("Papel inválido.")
        if password is not None and password != "" and len(password) < 8:
            raise ValueError("A senha deve ter pelo menos 8 caracteres.")

        with session_scope() as session:
            row = session.get(User, user_id)
            if not row:
                raise ValueError("Utilizador não encontrado.")
            duplicate = session.scalars(
                select(User)
                .where(func.lower(User.email) == normalized_email, User.id != user_id)
                .limit(1)
            ).first()
            if duplicate:
                raise ValueError("Este e-mail já está cadastrado.")
            self._ensure_not_last_admin_demotion(session, row, role)
            row.name = display_name
            row.email = normalized_email
            row.role = role
            if password:
                row.password_hash = hash_password(password)
            session.flush()
            session.refresh(row)
            return _to_user_record(row)

    def delete(self, user_id: int) -> bool:
        """Remove conta local. Matérias ficam com ``user_id`` nulo (SET NULL)."""
        with session_scope() as session:
            row = session.get(User, user_id)
            if not row:
                return False
            if row.role == UserRole.ADMIN.value:
                admins = int(
                    session.scalar(
                        select(func.count(User.id)).where(User.role == UserRole.ADMIN.value)
                    )
                    or 0
                )
                if admins <= 1:
                    raise ValueError("Não é possível excluir o último administrador.")
            session.delete(row)
            session.flush()
            return True


class AiUsageRepository:
    """Persistência e agregações de uso de tokens/custo de IA."""

    def insert(
        self,
        *,
        provider: str,
        model: str,
        task: str,
        source: str,
        prompt_tokens: int,
        completion_tokens: int,
        cost_usd: float,
        estimated: bool,
        session: Session | None = None,
    ) -> None:
        row = AiUsageLog(
            provider=provider[:32],
            model=model[:128],
            task=task[:64],
            source=source[:32],
            prompt_tokens=max(0, prompt_tokens),
            completion_tokens=max(0, completion_tokens),
            cost_usd=cost_usd,
            estimated=estimated,
        )
        if session is not None:
            session.add(row)
            session.flush()
            return
        with session_scope() as scoped:
            scoped.add(row)

    def aggregate_period(self, *, days: int) -> dict:
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        with session_scope() as session:
            row = session.execute(
                select(
                    func.count(AiUsageLog.id),
                    func.coalesce(func.sum(AiUsageLog.prompt_tokens), 0),
                    func.coalesce(func.sum(AiUsageLog.completion_tokens), 0),
                    func.coalesce(func.sum(AiUsageLog.cost_usd), 0.0),
                ).where(AiUsageLog.created_at >= cutoff)
            ).one()
        calls = int(row[0] or 0)
        prompt = int(row[1] or 0)
        completion = int(row[2] or 0)
        return {
            "calls": calls,
            "prompt_tokens": prompt,
            "completion_tokens": completion,
            "total_tokens": prompt + completion,
            "cost_usd": round(float(row[3] or 0.0), 4),
        }

    def totals_by_provider(self, *, days: int = 30) -> list[dict]:
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        with session_scope() as session:
            rows = session.execute(
                select(
                    AiUsageLog.provider,
                    func.count(AiUsageLog.id),
                    func.coalesce(func.sum(AiUsageLog.prompt_tokens), 0),
                    func.coalesce(func.sum(AiUsageLog.completion_tokens), 0),
                    func.coalesce(func.sum(AiUsageLog.cost_usd), 0.0),
                )
                .where(AiUsageLog.created_at >= cutoff)
                .group_by(AiUsageLog.provider)
                .order_by(func.sum(AiUsageLog.cost_usd).desc())
            ).all()
        return [
            {
                "provider": r[0],
                "calls": int(r[1] or 0),
                "prompt_tokens": int(r[2] or 0),
                "completion_tokens": int(r[3] or 0),
                "total_tokens": int(r[2] or 0) + int(r[3] or 0),
                "cost_usd": round(float(r[4] or 0.0), 4),
            }
            for r in rows
        ]

    def list_recent(self, limit: int = 15) -> list[dict]:
        with session_scope() as session:
            rows = session.scalars(
                select(AiUsageLog).order_by(AiUsageLog.created_at.desc()).limit(limit)
            ).all()
        items: list[dict] = []
        for row in rows:
            created = row.created_at
            if isinstance(created, datetime) and created.tzinfo:
                created = created.replace(tzinfo=None)
            items.append(
                {
                    "id": row.id,
                    "provider": row.provider,
                    "model": row.model,
                    "task": row.task,
                    "source": row.source,
                    "prompt_tokens": row.prompt_tokens,
                    "completion_tokens": row.completion_tokens,
                    "total_tokens": row.prompt_tokens + row.completion_tokens,
                    "cost_usd": row.cost_usd,
                    "estimated": row.estimated,
                    "created_at": created.strftime("%d/%m %H:%M")
                    if isinstance(created, datetime)
                    else str(created),
                }
            )
        return items
