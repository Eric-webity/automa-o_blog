"""Publicação no blog local do Content Studio (SQLite)."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass

from db.models import ArticleStatus
from db.repository import ArticleRecord, ArticleRepository

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class BlogPublishResult:
    """Resultado ao salvar matéria no blog local."""

    article_id: int
    status: str
    title: str


async def save_post_to_blog(
    *,
    title: str,
    markdown_content: str,
    json_index: dict | None = None,
    article_id: int | None = None,
    status: str = ArticleStatus.DRAFT.value,
    user_id: int | None = None,
) -> BlogPublishResult:
    """Cria ou atualiza matéria no histórico local (não envia para CMS externo)."""
    if not (markdown_content or "").strip():
        raise ValueError("O conteúdo do artigo está vazio.")

    clean_title = (title or "").strip() or "Sem título"
    if user_id is None:
        raise ValueError("user_id é obrigatório para salvar no histórico.")
    repo = ArticleRepository(user_id=user_id)

    def _persist() -> ArticleRecord:
        if article_id is not None:
            updated = repo.update(
                article_id,
                title=clean_title,
                markdown_content=markdown_content,
                json_index=json_index,
                status=status,
            )
            if updated is None:
                raise ValueError(f"Matéria #{article_id} não encontrada no histórico.")
            return updated
        return repo.create(
            title=clean_title,
            markdown_content=markdown_content,
            json_index=json_index,
            status=status,
            user_id=user_id,
        )

    try:
        record = await asyncio.to_thread(_persist)
    except Exception as exc:
        logger.exception("Falha ao salvar no blog local: %s", exc)
        raise

    return BlogPublishResult(
        article_id=record.id,
        status=record.status,
        title=record.title,
    )
