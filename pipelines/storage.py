"""Compatibilidade — use services.storage."""

from services.storage import (
    OUTPUT_DIR,
    ensure_output_dir,
    save_blog_artifacts,
    save_url_artifacts,
)

__all__ = [
    "OUTPUT_DIR",
    "ensure_output_dir",
    "save_blog_artifacts",
    "save_url_artifacts",
]
