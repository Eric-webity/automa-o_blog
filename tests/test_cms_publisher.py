"""Testes de publicação em CMS externo."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytest.importorskip("httpx")

from services.cms_publisher import publish_to_external_cms, send_test_cms_publish


@pytest.mark.asyncio
async def test_publish_skips_when_url_missing() -> None:
    with patch("services.cms_publisher.load_production_settings") as load:
        load.return_value = MagicMock(cms_publish_url="", cms_default_status="draft")
        result = await publish_to_external_cms(
            title="T",
            markdown_content="# Corpo",
        )
    assert result.success is False
    assert "não configurada" in result.message.lower()


@pytest.mark.asyncio
async def test_publish_success_parses_response() -> None:
    mock_response = MagicMock()
    mock_response.content = b'{"id": 42, "url": "https://cms.example/post/42"}'
    mock_response.json.return_value = {"id": 42, "url": "https://cms.example/post/42"}
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    settings = MagicMock(
        cms_publish_url="https://cms.example/api/posts",
        cms_publish_token="secret",
        cms_default_status="draft",
    )

    with (
        patch("services.cms_publisher.load_production_settings", return_value=settings),
        patch("services.cms_publisher.httpx.AsyncClient", return_value=mock_client),
    ):
        result = await publish_to_external_cms(
            title="Título",
            markdown_content="# Olá",
            slug="ola",
        )

    assert result.success is True
    assert result.external_id == "42"
    assert result.url == "https://cms.example/post/42"


@pytest.mark.asyncio
async def test_send_test_delegates_to_publish() -> None:
    with patch(
        "services.cms_publisher.publish_to_external_cms",
        new_callable=AsyncMock,
    ) as pub:
        pub.return_value = MagicMock(success=True, message="ok")
        result = await send_test_cms_publish()
    assert result.success is True
    pub.assert_awaited_once()
