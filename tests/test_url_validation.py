"""Testes de validação de URL (anti-SSRF)."""

import pytest

from services.url_security import URLValidationError, validate_reference_urls, validate_url


def test_validate_url_accepts_public():
    assert validate_url("https://example.com/article").startswith("https://")


def test_validate_url_blocks_localhost():
    with pytest.raises(URLValidationError):
        validate_url("http://localhost/admin")


def test_validate_url_blocks_private_ip():
    with pytest.raises(URLValidationError):
        validate_url("http://192.168.1.1/internal")


def test_validate_url_blocks_metadata_host():
    with pytest.raises(URLValidationError):
        validate_url("http://metadata.google.internal/computeMetadata/v1/")


def test_validate_url_blocks_decimal_ip():
    with pytest.raises(URLValidationError):
        validate_url("http://2130706433/")  # 127.0.0.1


def test_validate_url_blocks_file_scheme():
    with pytest.raises(URLValidationError):
        validate_url("file:///etc/passwd")


def test_validate_url_blocks_embedded_credentials():
    with pytest.raises(URLValidationError):
        validate_url("http://user:pass@example.com/")


def test_validate_reference_urls_dedupes():
    valid, errors = validate_reference_urls(
        ["https://example.com/a", "https://example.com/a"]
    )
    assert len(valid) == 1
    assert not errors


def test_validate_reference_urls_rejects_bad_with_errors():
    valid, errors = validate_reference_urls(
        ["https://example.com/ok", "http://127.0.0.1/secret"]
    )
    assert len(valid) == 1
    assert len(errors) == 1


def test_validate_reference_urls_max_limit(monkeypatch):
    monkeypatch.setenv("GEO_MAX_REFERENCE_URLS", "2")
    with pytest.raises(URLValidationError, match="Máximo"):
        validate_reference_urls(
            ["https://a.com", "https://b.com", "https://c.com"],
            max_count=None,
        )
