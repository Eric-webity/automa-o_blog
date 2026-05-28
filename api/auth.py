"""Autenticação da API REST."""

from __future__ import annotations

import logging

from fastapi import Header, HTTPException, status

from config.production import load_production_settings

logger = logging.getLogger(__name__)


def verify_api_key(
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    authorization: str | None = Header(default=None),
) -> None:
    """Valida chave de API quando exigida pelo ambiente."""
    settings = load_production_settings()
    if not settings.api_enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="API desativada (GEO_API_ENABLED=false).",
        )
    if not settings.require_api_key:
        return

    token = (x_api_key or "").strip()
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization[7:].strip()

    if not token or token != settings.api_key:
        logger.warning("Tentativa de acesso à API com chave inválida.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Chave de API inválida ou ausente.",
        )
