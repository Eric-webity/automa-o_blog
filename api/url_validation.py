"""Validação de URLs nos pedidos da API REST."""

from __future__ import annotations

from fastapi import HTTPException, status

from services.url_security import URLValidationError, validate_reference_urls


def validated_reference_urls(urls: list[str] | None) -> list[str]:
    """
    Valida ``reference_urls`` antes de fetch/geração.

    Raises:
        HTTPException 400: URL inválida, limite excedido ou risco SSRF.
    """
    if not urls:
        return []
    try:
        valid, errors = validate_reference_urls(urls)
    except URLValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": str(exc), "code": "url_validation"},
        ) from exc
    if errors:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": "Uma ou mais URLs de referência foram rejeitadas.",
                "code": "url_blocked",
                "errors": errors,
            },
        )
    return valid
