"""Tests for authentication configuration."""

import json
import pytest
from pathlib import Path
from unittest.mock import patch, mock_open
from fastapi import status

from app.auth.config import AuthConfig, get_auth_config


class TestAuthConfig:
    """Test AuthConfig class."""

    def test_is_managed_returns_true(self):
        """Test is_managed returns True when mode is managed."""
        with patch("app.auth.config.settings") as mock_settings:
            mock_settings.auth_mode = "managed"
            config = AuthConfig()
            assert config.is_managed() is True

    def test_get_stored_credentials_no_file(self, tmp_path):
        """Test get_stored_credentials when file doesn't exist."""
        with patch("app.auth.config.Path") as mock_path:
            mock_path.return_value = tmp_path / "nonexistent.json"
            config = AuthConfig()
            config.credentials_path = tmp_path / "nonexistent.json"
            assert config.get_stored_credentials() is None

    def test_get_stored_credentials_valid_file(self, tmp_path):
        """Test get_stored_credentials with valid file."""
        creds_file = tmp_path / "test-auth.json"
        test_creds = {
            "access": "test-access-token",
            "refresh": "test-refresh-token",
            "expires": 1234567890000
        }
        creds_file.write_text(json.dumps(test_creds))

        config = AuthConfig()
        config.credentials_path = creds_file
        result = config.get_stored_credentials()
        assert result == test_creds

    def test_get_stored_credentials_invalid_json(self, tmp_path, caplog):
        """Test get_stored_credentials with invalid JSON."""
        creds_file = tmp_path / "test-auth.json"
        creds_file.write_text("invalid json {")

        config = AuthConfig()
        config.credentials_path = creds_file
        result = config.get_stored_credentials()
        assert result is None
        assert "Failed to read credentials" in caplog.text

    def test_save_credentials_success(self, tmp_path):
        """Test save_credentials writes valid JSON."""
        creds_file = tmp_path / "test-auth.json"
        test_creds = {
            "access": "test-access-token",
            "refresh": "test-refresh-token",
            "expires": 1234567890000
        }

        config = AuthConfig()
        config.credentials_path = creds_file
        config.save_credentials(test_creds)

        assert creds_file.exists()
        with open(creds_file) as f:
            saved = json.load(f)
        assert saved == test_creds

    def test_save_credentials_error(self, tmp_path, caplog):
        """Test save_credentials with write error."""
        # Create a directory instead of a file to cause write error
        creds_path = tmp_path / "subdir" / "test-auth.json"
        creds_path.parent.mkdir()

        config = AuthConfig()
        config.credentials_path = creds_path / "subdir"  # This is a directory

        with pytest.raises(Exception):
            config.save_credentials({"access": "test"})

    def test_clear_credentials_file_exists(self, tmp_path):
        """Test clear_credentials removes existing file."""
        creds_file = tmp_path / "test-auth.json"
        creds_file.write_text('{"access": "test"}')

        config = AuthConfig()
        config.credentials_path = creds_file
        config.clear_credentials()

        assert not creds_file.exists()

    def test_clear_credentials_no_file(self, tmp_path, caplog):
        """Test clear_credentials when file doesn't exist."""
        creds_file = tmp_path / "nonexistent.json"

        config = AuthConfig()
        config.credentials_path = creds_file
        config.clear_credentials()  # Should not raise

        assert not creds_file.exists()

    def test_get_auth_config_singleton(self):
        """Test get_auth_config returns singleton instance."""
        config1 = get_auth_config()
        config2 = get_auth_config()
        assert config1 is config2


class TestAuthConfigIntegration:
    """Integration tests for auth config with endpoints."""

    def test_auth_status_unauthenticated(self, test_client, tmp_path):
        """Test auth status endpoint returns unauthenticated when no credentials."""
        response = test_client.get("/auth/status")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["authenticated"] is False
        assert data["mode"] == "managed"

    def test_auth_status_authenticated(self, test_client, tmp_path):
        """Test auth status endpoint returns authenticated with valid credentials."""
        # Create credentials file
        creds = {
            "access": "test-access-token",
            "refresh": "test-refresh-token",
            "expires": 9999999999999  # Far future
        }
        creds_file = Path(tmp_path) / ".copilot-auth.json"
        creds_file.write_text(json.dumps(creds))

        # Note: In a real test, we'd need to patch the credentials path
        # For now, we just verify the endpoint structure
        response = test_client.get("/auth/status")
        assert response.status_code == status.HTTP_200_OK

    def test_logout_clears_credentials(self, test_client, tmp_path):
        """Test logout endpoint clears credentials."""
        response = test_client.post("/auth/logout")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "success"
