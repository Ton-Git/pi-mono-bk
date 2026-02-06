"""Pytest configuration and fixtures."""

import pytest
from typing import Generator
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def test_client() -> Generator:
    """Create a test client for FastAPI."""
    with TestClient(app) as client:
        yield client


@pytest.fixture
def sample_openai_request():
    """Sample OpenAI chat completion request."""
    return {
        "model": "claude-sonnet-4.5",
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello!"},
        ],
        "stream": False,
    }


@pytest.fixture
def sample_anthropic_request():
    """Sample Anthropic message request."""
    return {
        "model": "claude-sonnet-4.5",
        "max_tokens": 1024,
        "messages": [
            {"role": "user", "content": "Hello!"},
        ],
        "stream": False,
    }


@pytest.fixture
def sample_auth_headers():
    """Sample authorization headers."""
    return {"Authorization": "Bearer test-copilot-token"}
