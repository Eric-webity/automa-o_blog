"""Compatibilidade — use services.*_pipeline."""

from services.blog_pipeline import BlogResult, run_blog_pipeline, run_blog_pipeline_async
from services.url_pipeline import UrlPipelineResult, run_url_pipeline

__all__ = [
    "BlogResult",
    "UrlPipelineResult",
    "run_blog_pipeline",
    "run_blog_pipeline_async",
    "run_url_pipeline",
]

