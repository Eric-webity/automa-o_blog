"""Persistência de ficheiros gerados."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = ROOT / "output"


def ensure_output_dir() -> Path:
    OUTPUT_DIR.mkdir(exist_ok=True)
    return OUTPUT_DIR


def save_blog_artifacts(
    slug: str,
    markdown: str,
    meta: dict,
    ai_index: dict | None = None,
) -> tuple[str, str, str | None]:
    ensure_output_dir()
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    md_path = OUTPUT_DIR / f"blog_{slug}_{ts}.md"
    meta_path = OUTPUT_DIR / f"blog_{slug}_{ts}_meta.json"
    md_path.write_text(markdown, encoding="utf-8")
    meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
    index_path: str | None = None
    if ai_index:
        ip = OUTPUT_DIR / f"blog_{slug}_{ts}_indice.json"
        ip.write_text(json.dumps(ai_index, indent=2, ensure_ascii=False), encoding="utf-8")
        index_path = str(ip)
    return str(md_path), str(meta_path), index_path


def save_url_artifacts(
    ai_index: dict,
    markdown: str,
) -> tuple[str, str]:
    ensure_output_dir()
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    index_path = OUTPUT_DIR / f"indice_{ts}.json"
    article_path = OUTPUT_DIR / f"artigo_{ts}.md"
    index_path.write_text(json.dumps(ai_index, indent=2, ensure_ascii=False), encoding="utf-8")
    article_path.write_text(markdown, encoding="utf-8")
    return str(index_path), str(article_path)
