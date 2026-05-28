"""Repositório de matérias no blog local (Content Studio)."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from db.database import session_scope
from db.models import Article, ArticleStatus

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

        cutoff = datetime.utcnow() - timedelta(days=days)
        with session_scope() as session:
            count = session.scalar(
                select(func.count(Article.id)).where(Article.created_at >= cutoff)
            )
            return int(count or 0)
