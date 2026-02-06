"""Tests for Anthropic-compatible API endpoints."""

import pytest
from fastapi import status


class TestAnthropicModelsEndpoint:
    """Test /v1/models endpoint."""

    def test_list_models(self, test_client):
        """Test listing models."""
        response = test_client.get("/v1/models")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        # /v1/models returns OpenAI format (registered first)
        assert data["object"] == "list"
        assert "data" in data


class TestAnthropicMessagesEndpoint:
    """Test /v1/messages endpoint."""

    def test_request_validation(self, test_client):
        """Test request validation."""
        # Missing model field
        request = {
            "max_tokens": 1024,
            "messages": [{"role": "user", "content": "Hi"}],
        }
        response = test_client.post("/v1/messages", json=request)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    def test_missing_max_tokens(self, test_client):
        """Test request without max_tokens."""
        request = {
            "model": "claude-sonnet-4.5",
            "messages": [{"role": "user", "content": "Hi"}],
        }
        response = test_client.post("/v1/messages", json=request)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
