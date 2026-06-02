"""Repositório de matérias no blog local (Content Studio)."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from core.passwords import hash_password, verify_password
from db.database import session_scope
from db.models import Article, ArticleStatus, BlogProfile, User

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
    )


class ArticleRepository:
    """CRUD de matérias do blog local."""

    def create(
        self,
        *,
        title: str,
        markdown_content: str,
        json_index: dict | None = None,
        status: str = ArticleStatus.COMPLETED.value,
        session: Session | None = None,
    ) -> ArticleRecord:
        """Persiste uma nova matéria."""
        payload = json.dumps(json_index, ensure_ascii=False) if json_index else None
        article = Article(
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
            if not row:
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

    def list_all(self, limit: int = 200) -> list[ArticleRecord]:
        """Lista matérias mais recentes primeiro."""
        with session_scope() as session:
            rows = session.scalars(
                select(Article).order_by(Article.created_at.desc()).limit(limit)
            ).all()
            return [_to_record(row) for row in rows]

    def get_by_id(self, article_id: int) -> ArticleRecord | None:
        """Busca matéria por identificador."""
        with session_scope() as session:
            row = session.get(Article, article_id)
            return _to_record(row) if row else None

    def delete(self, article_id: int) -> bool:
        """Remove matéria do histórico."""
        with session_scope() as session:
            row = session.get(Article, article_id)
            if not row:
                return False
            session.delete(row)
            return True

    def count_stats(self) -> dict[str, int | float | dict[str, int]]:
        """Agrega métricas para dashboard e API."""
        with session_scope() as session:
            total = int(session.scalar(select(func.count(Article.id))) or 0)
            rows = session.execute(
                select(Article.status, Article.markdown_content)
            ).all()
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
            rows = session.scalars(select(Article.json_index)).all()
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
            count = session.scalar(
                select(func.count(Article.id)).where(Article.created_at >= cutoff)
            )
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


class UserRepository:
    """Registo e autenticação de contas locais."""

    def get_by_email(self, email: str) -> UserRecord | None:
        normalized = email.strip().lower()
        with session_scope() as session:
            row = session.scalars(
                select(User).where(func.lower(User.email) == normalized).limit(1)
            ).first()
            if not row:
                return None
            return UserRecord(id=row.id, name=row.name, email=row.email)

    def email_exists(self, email: str) -> bool:
        return self.get_by_email(email) is not None

    def create(self, *, name: str, email: str, password: str) -> UserRecord:
        normalized_email = email.strip().lower()
        display_name = name.strip()[:200]
        with session_scope() as session:
            existing = session.scalars(
                select(User).where(func.lower(User.email) == normalized_email).limit(1)
            ).first()
            if existing:
                raise ValueError("Este e-mail já está cadastrado.")
            row = User(
                name=display_name,
                email=normalized_email,
                password_hash=hash_password(password),
            )
            session.add(row)
            session.flush()
            session.refresh(row)
            return UserRecord(id=row.id, name=row.name, email=row.email)

    def verify_credentials(self, email: str, password: str) -> UserRecord | None:
        normalized = email.strip().lower()
        with session_scope() as session:
            row = session.scalars(
                select(User).where(func.lower(User.email) == normalized).limit(1)
            ).first()
            if not row or not verify_password(password, row.password_hash):
                return None
            return UserRecord(id=row.id, name=row.name, email=row.email)


@dataclass
class UserRecord:
    """DTO de utilizador registado."""

    id: int
    name: str
    email: str


class UserRepository:
    """Registo e autenticação de contas locais."""

    def get_by_email(self, email: str) -> UserRecord | None:
        normalized = email.strip().lower()
        with session_scope() as session:
            row = session.scalars(
                select(User).where(func.lower(User.email) == normalized).limit(1)
            ).first()
            if not row:
                return None
            return UserRecord(id=row.id, name=row.name, email=row.email)

    def email_exists(self, email: str) -> bool:
        return self.get_by_email(email) is not None

    def create(self, *, name: str, email: str, password: str) -> UserRecord:
        normalized_email = email.strip().lower()
        display_name = name.strip()[:200]
        with session_scope() as session:
            existing = session.scalars(
                select(User).where(func.lower(User.email) == normalized_email).limit(1)
            ).first()
            if existing:
                raise ValueError("Este e-mail já está cadastrado.")
            row = User(
                name=display_name,
                email=normalized_email,
                password_hash=hash_password(password),
            )
            session.add(row)
            session.flush()
            session.refresh(row)
            return UserRecord(id=row.id, name=row.name, email=row.email)

    def verify_credentials(self, email: str, password: str) -> UserRecord | None:
        normalized = email.strip().lower()
        with session_scope() as session:
            row = session.scalars(
                select(User).where(func.lower(User.email) == normalized).limit(1)
            ).first()
            if not row or not verify_password(password, row.password_hash):
                return None
            return UserRecord(id=row.id, name=row.name, email=row.email)
