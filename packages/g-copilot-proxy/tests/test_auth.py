"""Tests for authentication."""

import pytest
from fastapi import status


class TestAuthEndpoints:
    """Test authentication endpoints."""

    def test_get_auth_config(self, test_client):
        """Test getting auth configuration."""
        response = test_client.get("/auth/config")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "mode" in data
        assert data["mode"] == "managed"

    def test_get_auth_status(self, test_client):
        """Test auth status."""
        response = test_client.get("/auth/status")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["mode"] == "managed"
