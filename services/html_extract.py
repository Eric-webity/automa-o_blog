"""Extração de título, headings e texto a partir de HTML."""

from __future__ import annotations

import re
from dataclasses import dataclass

from bs4 import BeautifulSoup

_MIN_PARAGRAPH_LEN = 40
_MAX_TEXT_LEN = 25_000


@dataclass
class ParsedHtml:
    title: str
    text: str
    headings: list[str]


def parse_html(html: str, *, fallback_title: str = "") -> ParsedHtml:
    """Converte HTML em título, headings e corpo de texto."""
    soup = BeautifulSoup(html or "", "html.parser")

    for tag in soup(["script", "style", "nav", "footer", "header", "aside", "noscript"]):
        tag.decompose()

    title = ""
    if soup.title and soup.title.string:
        title = soup.title.string.strip()
    h1 = soup.find("h1")
    if h1:
        title = h1.get_text(strip=True) or title
    if not title:
        title = fallback_title

    headings = [
        h.get_text(strip=True)
        for h in soup.find_all(["h1", "h2", "h3"])
        if h.get_text(strip=True)
    ][:12]

    paragraphs = [
        p.get_text(strip=True)
        for p in soup.find_all("p")
        if len(p.get_text(strip=True)) > _MIN_PARAGRAPH_LEN
    ]
    text = "\n\n".join(paragraphs)
    if not text:
        text = soup.get_text(separator="\n", strip=True)
    text = re.sub(r"\n{3,}", "\n\n", text)[:_MAX_TEXT_LEN]

    return ParsedHtml(title=title, text=text, headings=headings)
