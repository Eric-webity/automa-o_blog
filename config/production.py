"""Configurações de ambiente para produção."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class ProductionSettings:
    """Parâmetros carregados do .env para API e integrações."""

    env: str
    api_enabled: bool
    api_key: str
    webhook_url: str
    webhook_secret: str
    cms_publish_url: str
    cms_publish_token: str
    cms_default_status: str
    require_api_key: bool


def load_production_settings() -> ProductionSettings:
    """Lê variáveis de ambiente de produção."""
    env = (os.getenv("GEO_ENV") or "development").strip().lower()
    api_key = (os.getenv("GEO_API_KEY") or "").strip()
    api_enabled = os.getenv("GEO_API_ENABLED", "true").strip().lower() in (
        "1",
        "true",
        "yes",
    )
    require_api_key = env == "production" or bool(api_key)
    return ProductionSettings(
        env=env,
        api_enabled=api_enabled,
        api_key=api_key,
        webhook_url=(os.getenv("GEO_WEBHOOK_URL") or "").strip(),
        webhook_secret=(os.getenv("GEO_WEBHOOK_SECRET") or "").strip(),
        cms_publish_url=(os.getenv("GEO_CMS_PUBLISH_URL") or "").strip(),
        cms_publish_token=(os.getenv("GEO_CMS_PUBLISH_TOKEN") or "").strip(),
        cms_default_status=(os.getenv("GEO_CMS_DEFAULT_STATUS") or "draft").strip(),
        require_api_key=require_api_key,
    )
