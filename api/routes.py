"""Rotas REST v1 (FastAPI APIRouter)."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime

from fastapi import APIRouter, Depends, FastAPI, HTTPException, status
from nicegui import app as nicegui_app

from api.auth import verify_api_key
from api.schemas import (
    ArticleDetail,
    ArticleSummary,
    GenerateArticleRequest,
    GenerateArticleResponse,
    HealthResponse,
    PublishRequest,
    PublishResponse,
    StatsResponse,
)
from db.repository import ArticleRepository
from services.ai_manager import AIManager
from services.analytics import get_dashboard_stats
from services.blog import BlogBrief
from services.blog_pipeline import run_blog_pipeline
from services.cms_publisher import publish_to_external_cms
from services.webhook_notifier import notify_article_generated

logger = logging.getLogger(__name__)
API_VERSION = "1.0.0"

public_router = APIRouter(tags=["api"])
v1_router = APIRouter(prefix="/v1", tags=["api-v1"], dependencies=[Depends(verify_api_key)])


def _word_count(text: str) -> int:
    return len((text or "").split())


def _record_to_summary(record) -> ArticleSummary:
    created = record.created_at
    if isinstance(created, datetime) and created.tzinfo:
        created = created.replace(tzinfo=None)
    return ArticleSummary(
        id=record.id,
        title=record.title,
        status=record.status,
        created_at=created.isoformat() if isinstance(created, datetime) else str(created),
        word_count=_word_count(record.markdown_content),
    )


@public_router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    from config.production import load_production_settings

    settings = load_production_settings()
    return HealthResponse(status="ok", version=API_VERSION, env=settings.env)


@v1_router.get("/stats", response_model=StatsResponse)
def stats() -> StatsResponse:
    data = get_dashboard_stats()
    return StatsResponse(
        total_articles=data["total_articles"],
        articles_last_7_days=data["articles_last_7_days"],
        by_status=data["by_status"],
        avg_word_count=data["avg_word_count"],
        llm_articles=data["llm_articles"],
        local_articles=data["local_articles"],
        ready_providers=data["ready_providers"],
        api_key_configured=data["api_key_configured"],
        storage_db_bytes=data["storage_db_bytes"],
        storage_output_bytes=data["storage_output_bytes"],
    )


@v1_router.get("/articles", response_model=list[ArticleSummary])
def list_articles(limit: int = 50) -> list[ArticleSummary]:
    records = ArticleRepository().list_all(limit=min(limit, 200))
    return [_record_to_summary(r) for r in records]


@v1_router.get("/articles/{article_id}", response_model=ArticleDetail)
def get_article(article_id: int) -> ArticleDetail:
    record = ArticleRepository().get_by_id(article_id)
    if not record:
        raise HTTPException(status_code=404, detail="Matéria não encontrada.")
    summary = _record_to_summary(record)
    return ArticleDetail(
        **summary.model_dump(),
        markdown_content=record.markdown_content,
        json_index=record.json_index,
    )


@v1_router.delete("/articles/{article_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_article(article_id: int) -> None:
    if not ArticleRepository().delete(article_id):
        raise HTTPException(status_code=404, detail="Matéria não encontrada.")


@v1_router.post("/articles/generate", response_model=GenerateArticleResponse)
async def generate_article(body: GenerateArticleRequest) -> GenerateArticleResponse:
    brief = BlogBrief(
        topic=body.topic.strip(),
        reference_urls=body.reference_urls,
        target_keywords=body.keywords,
        audience=body.audience,
        tone=body.tone,
        word_count=body.word_count,
        brand_name=body.brand_name,
        cta=body.cta,
        include_faq=body.include_faq,
        angle=body.angle,
    )
    try:
        mgr = AIManager() if body.use_llm else None
        result = await asyncio.to_thread(
            run_blog_pipeline,
            brief,
            use_advanced=body.use_advanced,
            use_llm=body.use_llm,
            provider=body.provider,
            manager=mgr,
            persist=body.save_to_db,
        )
    except Exception as exc:
        logger.exception("API generate failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    pkg = result.package
    response = GenerateArticleResponse(
        article_id=result.article_id if body.save_to_db else None,
        title=pkg.meta_title,
        slug=pkg.slug,
        markdown_content=pkg.markdown,
        meta=result.meta_payload,
        generation_mode=pkg.generation_mode,
        word_count_actual=pkg.word_count_actual,
        word_count_target=pkg.word_count_target,
        fallback_reason=result.fallback_reason,
        warning=result.warning,
        similarity_warning=result.similarity_warning,
        warnings=result.warnings,
        artifact_paths={
            "markdown": result.md_path,
            "meta": result.meta_path,
            "index": result.index_path,
        },
    )
    if body.notify_webhook:
        await notify_article_generated(response.model_dump())
    return response


@v1_router.post("/articles/publish", response_model=PublishResponse)
async def publish_article(body: PublishRequest) -> PublishResponse:
    title = body.title
    markdown = body.markdown_content
    if body.article_id:
        record = ArticleRepository().get_by_id(body.article_id)
        if not record:
            raise HTTPException(status_code=404, detail="Matéria não encontrada.")
        title = title or record.title
        markdown = markdown or record.markdown_content

    if not markdown or not title:
        raise HTTPException(
            status_code=400,
            detail="Informe article_id ou title + markdown_content.",
        )

    result = await publish_to_external_cms(
        title=title,
        markdown_content=markdown,
        meta_title=body.meta_title,
        meta_description=body.meta_description,
        slug=body.slug,
        status=body.status,
    )
    return PublishResponse(
        success=result.success,
        external_id=result.external_id,
        message=result.message,
        url=result.url,
    )


def create_api_app() -> FastAPI:
    """App FastAPI isolada (testes e integrações sem NiceGUI)."""
    api = FastAPI(title="GEO Extractor API", version=API_VERSION)
    api.include_router(public_router, prefix="/api")
    api.include_router(v1_router, prefix="/api")
    return api


_ROUTES_REGISTERED = False


def register_api_routes() -> None:
    """Monta rotas no servidor NiceGUI."""
    global _ROUTES_REGISTERED
    if _ROUTES_REGISTERED:
        return
    _ROUTES_REGISTERED = True
    nicegui_app.include_router(public_router, prefix="/api")
    nicegui_app.include_router(v1_router, prefix="/api")
    logger.info("API REST v1 registada em /api/*")
