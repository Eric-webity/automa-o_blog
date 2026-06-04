"""Contratos JSON da API REST."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator

from services.url_security import URLValidationError, validate_reference_urls


class HealthResponse(BaseModel):
    """Resposta do health check."""

    status: str
    version: str
    env: str


class GenerateArticleRequest(BaseModel):
    """Pedido de geração de matéria via API."""

    topic: str = Field(..., min_length=3, max_length=500)
    reference_urls: list[str] = Field(
        default_factory=list,
        description="URLs públicas HTTP(S) apenas; máx. conforme GEO_MAX_REFERENCE_URLS.",
    )
    keywords: list[str] = Field(default_factory=list)

    @field_validator("reference_urls")
    @classmethod
    def validate_reference_urls_field(cls, value: list[str]) -> list[str]:
        if not value:
            return []
        try:
            valid, errors = validate_reference_urls(value)
        except URLValidationError as exc:
            raise ValueError(str(exc)) from exc
        if errors:
            preview = "; ".join(errors[:3])
            extra = f" (+{len(errors) - 3} mais)" if len(errors) > 3 else ""
            raise ValueError(f"URLs rejeitadas: {preview}{extra}") from None
        return valid
    audience: str = "Leitores interessados no tema"
    tone: str = "informativo"
    word_count: int = Field(default=2500, ge=500, le=6000)
    angle: str = ""
    brand_name: str = ""
    cta: str = ""
    include_faq: bool = True
    use_advanced: bool = True
    use_llm: bool = True
    provider: str | None = None
    save_to_db: bool = True
    notify_webhook: bool = True


class ArticleSummary(BaseModel):
    """Resumo de matéria para listagens."""

    id: int
    title: str
    status: str
    created_at: str
    word_count: int


class ArticleDetail(ArticleSummary):
    """Matéria completa."""

    markdown_content: str
    json_index: dict[str, Any] | None = None
    meta: dict[str, Any] | None = None


class GenerateArticleResponse(BaseModel):
    """Resposta após geração."""

    article_id: int | None
    title: str
    slug: str
    markdown_content: str
    meta: dict[str, Any]
    generation_mode: str
    word_count_actual: int
    word_count_target: int
    fallback_reason: str | None = None
    warning: str | None = None
    similarity_warning: str | None = None
    warnings: list[str] = Field(default_factory=list)
    artifact_paths: dict[str, str | None]


class StatsResponse(BaseModel):
    """Métricas agregadas para dashboard."""

    total_articles: int
    articles_last_7_days: int
    by_status: dict[str, int]
    avg_word_count: int
    llm_articles: int
    local_articles: int = 0
    ready_providers: list[str]
    api_key_configured: bool = False
    storage_db_bytes: int = 0
    storage_output_bytes: int = 0


class PublishRequest(BaseModel):
    """Pedido de publicação em CMS externo."""

    article_id: int | None = None
    title: str | None = None
    markdown_content: str | None = None
    meta_title: str | None = None
    meta_description: str | None = None
    slug: str | None = None
    status: str | None = None


class PublishResponse(BaseModel):
    """Resultado da publicação externa."""

    success: bool
    external_id: str | None = None
    message: str
    url: str | None = None
