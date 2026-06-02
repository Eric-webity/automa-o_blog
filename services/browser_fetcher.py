"""Fetch de páginas com navegador headless (Playwright) para sites em JavaScript."""

from __future__ import annotations

import logging
import os
import threading
from typing import Literal

logger = logging.getLogger(__name__)

_BROWSER_LOCK = threading.Lock()
_playwright_checked = False
_playwright_available = False

FetchMode = Literal["auto", "always", "never"]

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


def browser_fetch_mode() -> FetchMode:
    raw = (os.getenv("GEO_BROWSER_FETCH") or "auto").strip().lower()
    if raw in ("always", "on", "1", "true", "yes"):
        return "always"
    if raw in ("never", "off", "0", "false", "no"):
        return "never"
    return "auto"


def browser_fetch_enabled() -> bool:
    return browser_fetch_mode() != "never"


def browser_timeout_ms() -> int:
    raw = os.getenv("GEO_BROWSER_TIMEOUT_MS", "30000")
    try:
        return max(5000, min(120_000, int(raw)))
    except ValueError:
        return 30_000


def browser_wait_ms() -> int:
    raw = os.getenv("GEO_BROWSER_WAIT_MS", "2500")
    try:
        return max(0, min(15_000, int(raw)))
    except ValueError:
        return 2500


def min_text_for_http() -> int:
    """Texto mínimo (caracteres) para considerar fetch HTTP suficiente."""
    raw = os.getenv("GEO_BROWSER_MIN_TEXT", "200")
    try:
        return max(50, int(raw))
    except ValueError:
        return 200


def is_playwright_installed() -> bool:
    global _playwright_checked, _playwright_available
    if _playwright_checked:
        return _playwright_available
    _playwright_checked = True
    try:
        import playwright  # noqa: F401

        _playwright_available = True
    except ImportError:
        _playwright_available = False
    return _playwright_available


def fetch_page_html(url: str) -> str:
    """
    Abre a URL em Chromium headless e devolve o HTML renderizado.

    Levanta RuntimeError se Playwright não estiver instalado ou o browser falhar.
    """
    if not is_playwright_installed():
        raise RuntimeError(
            "Playwright não instalado. Execute: pip install playwright && playwright install chromium"
        )

    from playwright.sync_api import sync_playwright

    timeout = browser_timeout_ms()
    wait_after = browser_wait_ms()

    with _BROWSER_LOCK:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            try:
                page = browser.new_page(user_agent=USER_AGENT)
                page.set_default_timeout(timeout)
                page.goto(url, wait_until="domcontentloaded", timeout=timeout)
                if wait_after > 0:
                    page.wait_for_timeout(wait_after)
                return page.content()
            finally:
                browser.close()
