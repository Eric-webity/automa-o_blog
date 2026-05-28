"""Compatibilidade — importe de `core` e `services` em código novo."""

from core import (
    GeoInputs,
    GeoSkeleton,
    build_ai_index,
    extract_geo_signals,
    extract_insights_from_text,
    generate_geo_skeleton,
    validate_inputs,
)
from core.insight_extractor import ArticleInsight, extract_insights, merge_insights
from services.advanced_extractor import AdvancedExtractor, get_extractor
from services.ai_manager import AIManager
from services.article_fetcher import FetchedArticle, fetch_article, fetch_many
from services.article_writer import GeneratedArticle, generate_full_article
from services.blog import BlogBrief, BlogPostPackage, generate_blog_post, parse_keywords

__all__ = [
    "AIManager",
    "AdvancedExtractor",
    "ArticleInsight",
    "BlogBrief",
    "BlogPostPackage",
    "FetchedArticle",
    "GeneratedArticle",
    "GeoInputs",
    "GeoSkeleton",
    "build_ai_index",
    "extract_geo_signals",
    "extract_insights",
    "extract_insights_from_text",
    "fetch_article",
    "fetch_many",
    "generate_blog_post",
    "generate_full_article",
    "generate_geo_skeleton",
    "get_extractor",
    "merge_insights",
    "parse_keywords",
    "validate_inputs",
]
