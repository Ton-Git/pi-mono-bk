"""Tests for OpenAI-compatible API endpoints."""

import pytest
from fastapi import status


class TestOpenAIModelsEndpoint:
    """Test /v1/models endpoint."""

    def test_list_models(self, test_client):
        """Test listing models."""
        response = test_client.get("/v1/models")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["object"] == "list"
        assert "data" in data


class TestOpenAIChatCompletions:
    """Test /v1/chat/completions endpoint."""

    def test_request_validation(self, test_client):
        """Test request validation."""
        # Missing model field
        request = {"messages": [{"role": "user", "content": "Hi"}]}
        response = test_client.post("/v1/chat/completions", json=request)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    def test_invalid_message_role(self, test_client):
        """Test request with invalid message role."""
        request = {
            "model": "gpt-4",
            "messages": [{"role": "invalid", "content": "Hi"}],
        }
        response = test_client.post("/v1/chat/completions", json=request)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
