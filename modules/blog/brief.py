"""Compatibilidade — use services.blog.brief."""

from services.blog.brief import LONG_FORM_THRESHOLD, BlogBrief, parse_keywords

__all__ = ["BlogBrief", "LONG_FORM_THRESHOLD", "parse_keywords"]
