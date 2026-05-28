"""Briefing editorial para matérias de blog."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

LONG_FORM_THRESHOLD = 2600


def parse_keywords(raw: str) -> list[str]:
    if not raw.strip():
        return []
    return [k.strip() for k in re.split(r"[,;\n]", raw) if k.strip()]


@dataclass
class BlogBrief:
    """Parâmetros para criar uma matéria original para blog."""

    topic: str
    reference_urls: list[str] = field(default_factory=list)
    target_keywords: list[str] = field(default_factory=list)
    audience: str = "Leitores interessados no tema"
    tone: str = "informativo e acessível"
    word_count: int = 2500
    brand_name: str = ""
    cta: str = ""
    include_faq: bool = True
    angle: str = ""

    def is_long_form(self) -> bool:
        return self.word_count >= LONG_FORM_THRESHOLD

    def section_count(self) -> int:
        return max(6, min(12, self.word_count // 350))

    def words_per_section(self) -> int:
        return max(280, self.word_count // self.section_count())

    def primary_keyword(self) -> str:
        if self.target_keywords:
            return self.target_keywords[0]
        return self.topic.split()[0] if self.topic else "tema"
