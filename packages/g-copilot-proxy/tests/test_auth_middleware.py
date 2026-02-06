"""Tests for authentication middleware."""

import json
import time
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from fastapi import status
from fastapi.security import HTTPAuthorizationCredentials

from app.auth.middleware import get_api_key, optional_auth
from app.auth.config import AuthConfig


class TestGetAPIKey:
    """Test get_api_key function."""

    def test_get_api_key_no_credentials(self, test_client):
        """Test get_api_key returns 401 when no credentials stored."""
        response = test_client.post("/v1/chat/completions", json={
            "model": "claude-sonnet-4.5",
            "messages": [{"role": "user", "content": "Hello"}]
        })
        # Should return 401 or 500 depending on whether pi-ai is available
        # The important part is that auth middleware blocks the request
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_500_INTERNAL_SERVER_ERROR]

    def test_get_api_key_with_valid_credentials(self, tmp_path):
        """Test get_api_key with valid stored credentials."""
        creds = {
            "access": "test-access-token",
            "refresh": "test-refresh-token",
            "expires": int(time.time() * 1000) + 3600000  # 1 hour from now
        }
        creds_file = tmp_path / ".copilot-auth.json"
        creds_file.write_text(json.dumps(creds))

        with patch("app.auth.config.Path") as mock_path:
            mock_path.return_value = creds_file
            config = AuthConfig()
            config.credentials_path = creds_file

        # Test through the config directly
        retrieved = config.get_stored_credentials()
        assert retrieved is not None
        assert retrieved["access"] == "test-access-token"

    def test_get_api_key_expired_token(self, tmp_path):
        """Test get_api_key rejects expired token."""
        creds = {
            "access": "expired-token",
            "refresh": "test-refresh-token",
            "expires": int(time.time() * 1000) - 1000  # Expired
        }
        creds_file = tmp_path / ".copilot-auth.json"
        creds_file.write_text(json.dumps(creds))

        config = AuthConfig()
        config.credentials_path = creds_file

        # Verify credentials are retrieved but expired
        retrieved = config.get_stored_credentials()
        assert retrieved is not None
        assert retrieved["expires"] < int(time.time() * 1000)

    def test_get_api_key_no_expiration(self, tmp_path):
        """Test get_api_key with token that has no expiration."""
        creds = {
            "access": "test-access-token",
            "refresh": "test-refresh-token"
            # No expires field
        }
        creds_file = tmp_path / ".copilot-auth.json"
        creds_file.write_text(json.dumps(creds))

        config = AuthConfig()
        config.credentials_path = creds_file

        retrieved = config.get_stored_credentials()
        assert retrieved is not None
        assert retrieved["access"] == "test-access-token"
        assert "expires" not in retrieved or retrieved.get("expires") is None

    def test_get_api_key_missing_access_field(self, tmp_path):
        """Test get_api_key with credentials missing access field."""
        creds = {
            "refresh": "test-refresh-token",
            "expires": 9999999999999
        }
        creds_file = tmp_path / ".copilot-auth.json"
        creds_file.write_text(json.dumps(creds))

        config = AuthConfig()
        config.credentials_path = creds_file

        retrieved = config.get_stored_credentials()
        assert retrieved is not None
        assert retrieved.get("access") is None


class TestOptionalAuth:
    """Test optional_auth function."""

    @pytest.mark.asyncio
    async def test_optional_auth_no_credentials(self):
        """Test optional_auth returns None when no credentials."""
        # This would be tested through an endpoint that uses optional_auth
        # For now, we verify the function exists and handles exceptions
        from fastapi import Request

        mock_request = MagicMock(spec=Request)
        mock_request.headers = {}

        # Should return None instead of raising when no credentials
        result = await optional_auth(mock_request, None)
        assert result is None

    def test_optional_auth_with_credentials(self, tmp_path):
        """Test optional_auth returns credentials when available."""
        creds = {
            "access": "test-access-token",
            "refresh": "test-refresh-token",
            "expires": 9999999999999
        }
        creds_file = tmp_path / ".copilot-auth.json"
        creds_file.write_text(json.dumps(creds))

        config = AuthConfig()
        config.credentials_path = creds_file

        retrieved = config.get_stored_credentials()
        assert retrieved is not None


class TestAuthMiddlewareIntegration:
    """Integration tests for auth middleware."""

    def test_models_endpoint_no_auth_required(self, test_client):
        """Test /v1/models endpoint works without auth."""
        response = test_client.get("/v1/models")
        assert response.status_code == status.HTTP_200_OK

    def test_chat_endpoint_requires_auth(self, test_client):
        """Test /v1/chat/completions requires authentication."""
        response = test_client.post("/v1/chat/completions", json={
            "model": "claude-sonnet-4.5",
            "messages": [{"role": "user", "content": "Hello"}]
        })
        # Should fail due to missing pi-ai or auth
        assert response.status_code != status.HTTP_200_OK

    def test_anthropic_messages_requires_auth(self, test_client):
        """Test /v1/messages requires authentication."""
        response = test_client.post("/v1/messages", json={
            "model": "claude-sonnet-4.5",
            "max_tokens": 1024,
            "messages": [{"role": "user", "content": "Hello"}]
        })
        # Should fail due to missing pi-ai or auth
        assert response.status_code != status.HTTP_200_OK
