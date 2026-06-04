"""Modelos ORM para persistência local."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base declarativa SQLAlchemy."""


class ArticleStatus(StrEnum):
    """Estados possíveis de uma matéria salva."""

    DRAFT = "draft"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class UserRole(StrEnum):
    """Papel da conta no Content Studio."""

    USER = "user"
    ADMIN = "admin"


class Article(Base):
    """Matéria gerada e persistida no histórico do Content Studio."""

    __tablename__ = "articles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    markdown_content: Mapped[str] = mapped_column(Text, nullable=False, default="")
    json_index: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default=ArticleStatus.COMPLETED.value
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class User(Base):
    """Conta local do Content Studio."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    role: Mapped[str] = mapped_column(
        String(16), nullable=False, default=UserRole.USER.value
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class AiUsageLog(Base):
    """Registo de tokens e custo estimado por chamada de IA."""

    __tablename__ = "ai_usage_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    provider: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    model: Mapped[str] = mapped_column(String(128), nullable=False)
    task: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    source: Mapped[str] = mapped_column(String(32), nullable=False, default="general")
    prompt_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    completion_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cost_usd: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    estimated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )


class BlogProfile(Base):
    """Perfil do utilizador e metadados do blog local (registo único)."""

    __tablename__ = "blog_profile"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    email: Mapped[str] = mapped_column(String(320), nullable=False, default="")
    phone: Mapped[str] = mapped_column(String(50), nullable=False, default="")
    bio: Mapped[str] = mapped_column(Text, nullable=False, default="")
    title: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
