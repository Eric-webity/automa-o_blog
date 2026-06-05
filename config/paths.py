"""Caminhos raiz do projeto GEO Extractor (dev e executável)."""

from __future__ import annotations

import sys
from pathlib import Path


def _app_root() -> Path:
    """Diretório gravável: pasta do projeto ou pasta do .exe."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def _bundle_root() -> Path:
    """Recursos empacotados (PyInstaller _MEIPASS ou raiz do projeto)."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return _app_root()


def _resolve_config_dir() -> Path:
    """Config editável ao lado do .exe tem prioridade sobre o bundle."""
    beside = _app_root() / "config"
    if beside.is_dir() and (beside / "ai_providers.yaml").exists():
        return beside
    bundled = _bundle_root() / "config"
    if bundled.is_dir():
        return bundled
    return beside


ROOT = _app_root()
BUNDLE_ROOT = _bundle_root()
CONFIG_DIR = _resolve_config_dir()
OUTPUT_DIR = ROOT / "output"
DATA_DIR = ROOT / "data"
DB_PATH = DATA_DIR / "geo_extractor.db"
AI_PROVIDERS_YAML = CONFIG_DIR / "ai_providers.yaml"
ENV_PATH = ROOT / ".env"
SKILLS_DIR = _bundle_root() / "skills"
UI_STYLE_PATH = _bundle_root() / "ui" / "style.css"
if not UI_STYLE_PATH.is_file():
    UI_STYLE_PATH = ROOT / "ui" / "style.css"
UI_DESIGN_TOKENS_PATH = _bundle_root() / "ui" / "design_tokens.css"
if not UI_DESIGN_TOKENS_PATH.is_file():
    UI_DESIGN_TOKENS_PATH = ROOT / "ui" / "design_tokens.css"
