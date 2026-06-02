"""Testes de validação de URL."""

import pytest

from services.article_fetcher import URLValidationError, validate_url


def test_validate_url_accepts_public():
    assert validate_url("https://example.com/article").startswith("https://")


def test_validate_url_blocks_localhost():
    with pytest.raises(URLValidationError):
        validate_url("http://localhost/admin")


def test_validate_url_blocks_private_ip():
    with pytest.raises(URLValidationError):
        validate_url("http://192.168.1.1/internal")
