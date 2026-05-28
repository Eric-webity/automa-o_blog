"""Compatibilidade — use services.blog_pipeline."""

from services.blog_pipeline import BlogResult, run_blog_pipeline

__all__ = ["BlogResult", "run_blog_pipeline"]
