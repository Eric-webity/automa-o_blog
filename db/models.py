"""Modelos ORM para persistência local."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base declarativa SQLAlchemy."""


class ArticleStatus(StrEnum):
    """Estados possíveis de uma matéria salva."""

    DRAFT = "draft"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class Article(Base):
    """Matéria gerada e persistida no histórico do Content Studio."""

    __tablename__ = "articles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
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
