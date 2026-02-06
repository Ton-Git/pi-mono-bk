# Phase 5: Testing & Deployment

## Overview

Set up comprehensive testing, Docker deployment, and production configuration for `g-copilot-proxy`.

> **IMPORTANT: No commits should be made during implementation.** This is a planning-only repository. All code changes should be made in the actual implementation package, not committed to git during the planning phase.

## Testing Strategy

### Test Categories

1. **Unit Tests**: Test individual components in isolation
2. **Integration Tests**: Test component interactions
3. **API Tests**: Test endpoint behavior
4. **E2E Tests**: Test full request flows

### Test Tools

- **pytest**: Test framework
- **pytest-asyncio**: Async test support
- **pytest-cov**: Code coverage
- **httpx**: HTTP client for testing
- **respx**: HTTP mocking for external requests

## Step 1: Create Test Configuration

#### `tests/conftest.py`
```python
"""Pytest configuration and fixtures."""

import asyncio
import pytest
from typing import AsyncGenerator, Generator
from fastapi.testclient import TestClient
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.config import get_settings
from app.core import PiAIBridge


@pytest.fixture
def test_settings():
    """Get test settings."""
    return get_settings()


@pytest.fixture
def test_client() -> Generator:
    """Create a test client for FastAPI."""
    with TestClient(app) as client:
        yield client


@pytest.fixture
async def async_client() -> AsyncGenerator:
    """Create an async test client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.fixture
def mock_piai_bridge(monkeypatch):
    """Mock the pi-ai bridge for testing."""
    class MockBridge:
        async def get_models(self):
            return [
                {"id": "claude-sonnet-4.5", "name": "Claude Sonnet 4.5"},
                {"id": "gpt-4.1", "name": "GPT 4.1"},
            ]

        async def stream_completion_iter(self, *args, **kwargs):
            # Yield mock events
            yield {"type": "start", "partial": {"role": "assistant", "content": []}}
            yield {"type": "text_delta", "delta": "Hello", "partial": {"role": "assistant"}}
            yield {"type": "text_end", "content": "Hello", "partial": {"role": "assistant"}}
            yield {"type": "done", "reason": "stop", "message": {
                "role": "assistant",
                "content": [{"type": "text", "text": "Hello"}],
                "usage": {"input": 10, "output": 5, "totalTokens": 15},
                "stopReason": "stop",
            }}

    def mock_get_bridge():
        return MockBridge()

    monkeypatch.setattr("app.core.piai_bridge.get_piai_bridge", mock_get_bridge)
    monkeypatch.setattr("app.api.openai.chat.get_piai_bridge", mock_get_bridge)
    monkeypatch.setattr("app.api.anthropic.messages.get_piai_bridge", mock_get_bridge)

    return MockBridge()


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
```

#### `tests/__init__.py`
```python
"""Tests for g-copilot-proxy."""
```

## Step 2: Create Unit Tests

#### `tests/test_piai_bridge.py`
```python
"""Unit tests for pi-ai bridge."""

import pytest
from app.core.piai_bridge import PiAIBridge, PiAIBridgeError


class TestPiAIBridge:
    """Test pi-ai bridge functionality."""

    @pytest.mark.asyncio
    async def test_bridge_init_with_valid_path(self, tmp_path):
        """Test bridge initialization with valid path."""
        # Create a mock package.json
        (tmp_path / "package.json").write_text('{"name": "test"}')

        bridge = PiAIBridge(module_path=str(tmp_path))
        assert bridge.module_path == tmp_path.resolve()

    @pytest.mark.asyncio
    async def test_bridge_init_with_invalid_path(self):
        """Test bridge initialization with invalid path."""
        with pytest.raises(PiAIBridgeError) as exc_info:
            PiAIBridge(module_path="/nonexistent/path")
        assert "not found" in str(exc_info.value).lower()


class TestOpenAIMapper:
    """Test OpenAI request/response mapper."""

    def test_map_messages_with_system(self):
        """Test mapping messages with system prompt."""
        from app.core.mapper import OpenAIMapper

        messages = [
            {"role": "system", "content": "You are helpful"},
            {"role": "user", "content": "Hello"},
        ]

        piai_msgs, system = OpenAIMapper.map_openai_to_piai_messages(messages)

        assert system == "You are helpful"
        assert len(piai_msgs) == 1
        assert piai_msgs[0]["role"] == "user"

    def test_map_messages_with_tool_calls(self):
        """Test mapping messages with tool calls."""
        from app.core.mapper import OpenAIMapper

        messages = [
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "call_123",
                        "function": {
                            "name": "get_weather",
                            "parameters": {"location": "NYC"},
                        },
                    }
                ],
            }
        ]

        piai_msgs, _ = OpenAIMapper.map_openai_to_piai_messages(messages)

        assert len(piai_msgs) == 1
        assert piai_msgs[0]["role"] == "assistant"
        assert len(piai_msgs[0]["content"]) == 1
        assert piai_msgs[0]["content"][0]["type"] == "toolCall"

    def test_map_tools(self):
        """Test mapping tools to pi-ai format."""
        from app.core.mapper import OpenAIMapper

        tools = [
            {
                "type": "function",
                "function": {
                    "name": "get_weather",
                    "description": "Get weather",
                    "parameters": {
                        "type": "object",
                        "properties": {"location": {"type": "string"}},
                    },
                },
            }
        ]

        piai_tools = OpenAIMapper.map_openai_tools_to_piai(tools)

        assert len(piai_tools) == 1
        assert piai_tools[0]["name"] == "get_weather"
        assert piai_tools[0]["description"] == "Get weather"


class TestAnthropicMapper:
    """Test Anthropic request/response mapper."""

    def test_map_simple_messages(self):
        """Test mapping simple messages."""
        from app.core.mapper import AnthropicMapper

        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there"},
        ]

        piai_msgs, system = AnthropicMapper.map_anthropic_to_piai_messages(messages)

        assert system is None
        assert len(piai_msgs) == 2
        assert piai_msgs[0]["role"] == "user"
        assert piai_msgs[1]["role"] == "assistant"

    def test_map_messages_with_system(self):
        """Test mapping messages with separate system prompt."""
        from app.core.mapper import AnthropicMapper

        messages = [{"role": "user", "content": "Hello"}]
        system = "You are helpful"

        piai_msgs, returned_system = AnthropicMapper.map_anthropic_to_piai_messages(
            messages, system
        )

        assert returned_system == system
        assert len(piai_msgs) == 1
```

## Step 3: Create API Tests

#### `tests/test_openai_api.py`
```python
"""Tests for OpenAI-compatible API endpoints."""

import pytest
from fastapi import status


class TestOpenAIModelsEndpoint:
    """Test /v1/models endpoint."""

    def test_list_models(self, test_client, mock_piai_bridge):
        """Test listing models."""
        response = test_client.get("/v1/models")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["object"] == "list"
        assert "data" in data
        assert len(data["data"]) > 0

    def test_get_specific_model(self, test_client, mock_piai_bridge):
        """Test getting a specific model."""
        response = test_client.get("/v1/models/claude-sonnet-4.5")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == "claude-sonnet-4.5"


class TestOpenAIChatCompletions:
    """Test /v1/chat/completions endpoint."""

    def test_non_streaming_completion(self, test_client, mock_piai_bridge, sample_openai_request):
        """Test non-streaming chat completion."""
        response = test_client.post(
            "/v1/chat/completions",
            json=sample_openai_request,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["object"] == "chat.completion"
        assert "choices" in data
        assert len(data["choices"]) > 0
        assert "usage" in data

    def test_streaming_completion(self, test_client, mock_piai_bridge, sample_openai_request):
        """Test streaming chat completion."""
        sample_openai_request["stream"] = True

        response = test_client.post(
            "/v1/chat/completions",
            json=sample_openai_request,
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.headers["content-type"] == "text/event-stream"

        # Check SSE format
        content = response.text
        assert "data: " in content

    def test_completion_with_auth(self, test_client, mock_piai_bridge, sample_openai_request, sample_auth_headers):
        """Test completion with authorization header."""
        response = test_client.post(
            "/v1/chat/completions",
            json=sample_openai_request,
            headers=sample_auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK

    def test_invalid_model_resolution(self, test_client, mock_piai_bridge):
        """Test with an unknown model (should use as-is)."""
        request = {
            "model": "unknown-model-x",
            "messages": [{"role": "user", "content": "Test"}],
        }

        response = test_client.post("/v1/chat/completions", json=request)

        # Should still work, just pass through unknown model
        assert response.status_code == status.HTTP_200_OK


class TestOpenAIRequestValidation:
    """Test request validation."""

    def test_missing_model_field(self, test_client):
        """Test request without model field."""
        request = {"messages": [{"role": "user", "content": "Hi"}]}

        response = test_client.post("/v1/chat/completions", json=request)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_missing_messages_field(self, test_client):
        """Test request without messages field."""
        request = {"model": "gpt-4"}

        response = test_client.post("/v1/chat/completions", json=request)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_invalid_message_role(self, test_client):
        """Test request with invalid message role."""
        request = {
            "model": "gpt-4",
            "messages": [{"role": "invalid", "content": "Hi"}],
        }

        response = test_client.post("/v1/chat/completions", json=request)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
```

#### `tests/test_anthropic_api.py`
```python
"""Tests for Anthropic-compatible API endpoints."""

import pytest
from fastapi import status


class TestAnthropicModelsEndpoint:
    """Test /v1/models endpoint."""

    def test_list_models(self, test_client, mock_piai_bridge):
        """Test listing models."""
        response = test_client.get("/v1/models")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "data" in data
        assert "has_more" in data
        assert isinstance(data["data"], list)


class TestAnthropicMessagesEndpoint:
    """Test /v1/messages endpoint."""

    def test_non_streaming_message(self, test_client, mock_piai_bridge, sample_anthropic_request):
        """Test non-streaming message."""
        response = test_client.post(
            "/v1/messages",
            json=sample_anthropic_request,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["type"] == "message"
        assert data["role"] == "assistant"
        assert "content" in data
        assert "usage" in data

    def test_streaming_message(self, test_client, mock_piai_bridge, sample_anthropic_request):
        """Test streaming message."""
        sample_anthropic_request["stream"] = True

        response = test_client.post(
            "/v1/messages",
            json=sample_anthropic_request,
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.headers["content-type"] == "text/event-stream"

    def test_message_with_system_prompt(self, test_client, mock_piai_bridge):
        """Test message with system prompt."""
        request = {
            "model": "claude-sonnet-4.5",
            "max_tokens": 1024,
            "system": "You are a helpful assistant.",
            "messages": [{"role": "user", "content": "Hello"}],
        }

        response = test_client.post("/v1/messages", json=request)

        assert response.status_code == status.HTTP_200_OK

    def test_message_with_x_api_key(self, test_client, mock_piai_bridge, sample_anthropic_request):
        """Test message with x-api-key header."""
        response = test_client.post(
            "/v1/messages",
            json=sample_anthropic_request,
            headers={"x-api-key": "test-token"},
        )

        assert response.status_code == status.HTTP_200_OK


class TestAnthropicRequestValidation:
    """Test request validation."""

    def test_missing_model_field(self, test_client):
        """Test request without model field."""
        request = {
            "max_tokens": 1024,
            "messages": [{"role": "user", "content": "Hi"}],
        }

        response = test_client.post("/v1/messages", json=request)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_missing_max_tokens(self, test_client):
        """Test request without max_tokens."""
        request = {
            "model": "claude-sonnet-4.5",
            "messages": [{"role": "user", "content": "Hi"}],
        }

        response = test_client.post("/v1/messages", json=request)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
```

## Step 4: Create Auth Tests

#### `tests/test_auth.py`
```python
"""Tests for authentication."""

import pytest
from fastapi import status
from pathlib import Path


class TestAuthConfig:
    """Test auth configuration."""

    def test_default_passthrough_mode(self):
        """Test default passthrough mode."""
        from app.auth.config import get_auth_config

        config = get_auth_config()
        assert config.is_pass_through()
        assert not config.is_managed()

    def test_managed_mode(self, monkeypatch):
        """Test managed auth mode."""
        from app.auth.config import get_auth_config

        monkeypatch.setenv("AUTH_MODE", "managed")

        # Clear cache
        from app.auth.config import auth_config
        auth_config.mode = "managed"

        assert auth_config.is_managed()
        assert not auth_config.is_pass_through()


class TestAuthEndpoints:
    """Test authentication endpoints."""

    def test_get_auth_config(self, test_client):
        """Test getting auth configuration."""
        response = test_client.get("/auth/config")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "mode" in data

    def test_get_auth_status_passthrough(self, test_client):
        """Test auth status in passthrough mode."""
        response = test_client.get("/auth/status")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["mode"] == "passthrough"

    def test_login_in_passthrough_mode(self, test_client):
        """Test login endpoint in passthrough mode."""
        response = test_client.post("/auth/login", json={})

        # Should return error in passthrough mode
        assert response.status_code == status.HTTP_400_BAD_REQUEST
```

## Step 5: Create E2E Tests

#### `tests/test_e2e.py`
```python
"""End-to-end tests."""

import pytest
import json
from fastapi import status


class TestE2EOpenAI:
    """E2E tests for OpenAI API."""

    @pytest.mark.skipif(
        "not config.getoption('--run-e2e')",
        reason="E2E tests require --run-e2e flag"
    )
    def test_full_openai_flow(self, test_client):
        """Test complete OpenAI chat flow."""
        # List models
        models_response = test_client.get("/v1/models")
        assert models_response.status_code == status.HTTP_200_OK
        models = models_response.json()["data"]
        assert len(models) > 0

        # Create completion
        chat_response = test_client.post(
            "/v1/chat/completions",
            json={
                "model": models[0]["id"],
                "messages": [{"role": "user", "content": "Say 'test passed'"}],
            },
            headers={"Authorization": "Bearer test-token"},
        )
        assert chat_response.status_code == status.HTTP_200_OK


class TestE2EAnthropic:
    """E2E tests for Anthropic API."""

    @pytest.mark.skipif(
        "not config.getoption('--run-e2e')",
        reason="E2E tests require --run-e2e flag"
    )
    def test_full_anthropic_flow(self, test_client):
        """Test complete Anthropic message flow."""
        # List models
        models_response = test_client.get("/v1/models")
        assert models_response.status_code == status.HTTP_200_OK

        # Create message
        message_response = test_client.post(
            "/v1/messages",
            json={
                "model": "claude-sonnet-4.5",
                "max_tokens": 100,
                "messages": [{"role": "user", "content": "Say 'test passed'"}],
            },
            headers={"Authorization": "Bearer test-token"},
        )
        assert message_response.status_code == status.HTTP_200_OK
```

## Step 6: Update pyproject.toml

Add test configuration to `pyproject.toml`:

```toml
[tool.poetry.group.dev.dependencies]
pytest = "^8.3.0"
pytest-asyncio = "^0.24.0"
pytest-cov = "^6.0.0"
black = "^24.10.0"
ruff = "^0.8.0"
mypy = "^1.13.0"
httpx = "^0.28.0"
respx = "^0.22.0"

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
addopts = [
    "--strict-markers",
    "--strict-config",
    "-ra",
]
markers = [
    "e2e: marks tests as end-to-end (deselect with '-m \"not e2e\"')",
]

[tool.coverage.run]
source = ["app"]
omit = [
    "*/tests/*",
    "*/__pycache__/*",
]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "raise NotImplementedError",
    "if TYPE_CHECKING:",
]
```

## Step 7: Create Docker Configuration

#### `Dockerfile`
```dockerfile
# Multi-stage build for g-copilot-proxy

# Stage 1: Builder
FROM python:3.11-slim AS builder

# Install build dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    nodejs \
    npm \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install poetry

# Set working directory
WORKDIR /build

# Copy dependency files
COPY pyproject.toml poetry.lock* ./

# Configure Poetry
RUN poetry config virtualenvs.create false \
    && poetry config virtualenvs.in-project false

# Install dependencies
RUN poetry install --no-dev --no-root --no-interaction --no-ansi

# Stage 2: Runtime
FROM python:3.11-slim

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    nodejs \
    && rm -rf /var/lib/apt/lists/* \
    && useradd -m -u 1000 appuser

# Set working directory
WORKDIR /app

# Copy Python dependencies from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY --chown=appuser:appuser . .

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### `docker-compose.yml`
```yaml
version: "3.8"

services:
  g-copilot-proxy:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: g-copilot-proxy
    ports:
      - "8000:8000"
    environment:
      - APP_NAME=g-copilot-proxy
      - HOST=0.0.0.0
      - PORT=8000
      - LOG_LEVEL=INFO
      - AUTH_MODE=passthrough
      - PIAI_MODULE_PATH=/app/ai
      - CORS_ORIGINS=["*"]
    volumes:
      # Mount pi-ai module if running from monorepo
      - ../ai:/app/ai:ro
      # Persist OAuth credentials
      - ./data:/app/data
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 5s

  # Optional: Add monitoring with Prometheus
  prometheus:
    image: prom/prometheus:latest
    container_name: prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml:ro
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
    restart: unless-stopped

  # Optional: Add Grafana for dashboards
  grafana:
    image: grafana/grafana:latest
    container_name: grafana
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    volumes:
      - grafana-data:/var/lib/grafana
      - ./monitoring/grafana/dashboards:/etc/grafana/provisioning/dashboards:ro
    restart: unless-stopped

volumes:
  grafana-data:
```

#### `.dockerignore`
```
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
*.egg-info/
dist/
build/

# Testing
.pytest_cache/
.coverage
htmlcov/
.tox/

# IDE
.vscode/
.idea/
*.swp
*.swo

# Git
.git/
.gitignore

# Documentation
*.md
docs/

# Data
data/
.copilot-auth.json
.env

# Node modules (if any)
node_modules/
```

## Step 8: Create Monitoring Configuration

#### `monitoring/prometheus.yml`
```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'g-copilot-proxy'
    static_configs:
      - targets: ['g-copilot-proxy:8000']
    metrics_path: '/metrics'
```

#### `app/core/metrics.py`
```python
"""Prometheus metrics for monitoring."""

from prometheus_client import Counter, Histogram, Gauge, generate_latest
from prometheus_client.exposition import CONTENT_TYPE_LATEST
from fastapi import Response
import time

# Request metrics
request_count = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"]
)

request_duration = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration",
    ["method", "endpoint"]
)

# Active requests
active_requests = Gauge(
    "http_active_requests",
    "Number of active HTTP requests"
)

# Copilot API metrics
copilot_requests = Counter(
    "copilot_requests_total",
    "Total Copilot API requests",
    ["model", "status"]
)

copilot_request_duration = Histogram(
    "copilot_request_duration_seconds",
    "Copilot API request duration",
    ["model"]
)


async def metrics_endpoint():
    """Return Prometheus metrics."""
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )


class MetricsMiddleware:
    """Middleware to track request metrics."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Start timer
        start_time = time.time()
        active_requests.inc()

        # Wrap send to capture status code
        status_code = 200

        async def send_wrapper(message):
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            # Record metrics
            duration = time.time() - start_time
            active_requests.dec()

            request_count.labels(
                method=scope["method"],
                path=scope["path"],
                status=status_code
            ).inc()

            request_duration.labels(
                method=scope["method"],
                path=scope["path"]
            ).observe(duration)
```

## Step 9: Create Production Configuration

#### `docker-compose.prod.yml`
```yaml
version: "3.8"

services:
  g-copilot-proxy:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: g-copilot-proxy-prod
    ports:
      - "8000:8000"
    env_file:
      - .env.production
    volumes:
      - ../ai:/app/ai:ro
      - ./data:/app/data
    restart: always
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '0.5'
          memory: 512M
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

  nginx:
    image: nginx:alpine
    container_name: nginx-proxy
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./nginx/ssl:/etc/nginx/ssl:ro
    depends_on:
      - g-copilot-proxy
    restart: always
```

#### `.env.production.example`
```bash
# Production Configuration
APP_NAME=g-copilot-proxy
APP_VERSION=0.1.0
HOST=0.0.0.0
PORT=8000
DEBUG=false

# pi-ai Bridge
PIAI_MODULE_PATH=/app/ai
PIAI_NODE_PATH=node

# Authentication
AUTH_MODE=passthrough
API_KEY_HEADER=Authorization
API_KEY_PREFIX=Bearer

# CORS - Restrict in production
CORS_ORIGINS=["https://yourdomain.com"]

# Rate Limiting
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_PERIOD=60

# Logging
LOG_LEVEL=WARNING

# Monitoring
ENABLE_METRICS=true
```

#### `nginx/nginx.conf`
```nginx
events {
    worker_connections 1024;
}

http {
    upstream g_copilot_proxy {
        server g-copilot-proxy:8000;
    }

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;

    server {
        listen 80;
        server_name yourdomain.com;

        # Redirect to HTTPS
        return 301 https://$server_name$request_uri;
    }

    server {
        listen 443 ssl http2;
        server_name yourdomain.com;

        ssl_certificate /etc/nginx/ssl/cert.pem;
        ssl_certificate_key /etc/nginx/ssl/key.pem;
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers HIGH:!aNULL:!MD5;

        # Security headers
        add_header X-Frame-Options "SAMEORIGIN" always;
        add_header X-Content-Type-Options "nosniff" always;
        add_header X-XSS-Protection "1; mode=block" always;

        location / {
            limit_req zone=api_limit burst=20 nodelay;

            proxy_pass http://g_copilot_proxy;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;

            # SSE support
            proxy_buffering off;
            proxy_cache off;
            proxy_set_header Connection '';
            proxy_http_version 1.1;
            chunked_transfer_encoding off;
        }

        location /health {
            proxy_pass http://g_copilot_proxy/health;
            access_log off;
        }
    }
}
```

## Step 10: Create Deployment Scripts

#### `scripts/run_tests.sh`
```bash
#!/bin/bash
# Run all tests

set -e

echo "Running linters..."
poetry run ruff check app/
poetry run black --check app/
poetry run mypy app/

echo "Running unit tests..."
poetry run pytest tests/ -v --cov=app --cov-report=html

echo "Test coverage report: htmlcov/index.html"
```

#### `scripts/docker-build.sh`
```bash
#!/bin/bash
# Build Docker image

set -e

VERSION=${1:-latest}
IMAGE_NAME="g-copilot-proxy"

echo "Building Docker image: ${IMAGE_NAME}:${VERSION}"
docker build -t ${IMAGE_NAME}:${VERSION} .
docker tag ${IMAGE_NAME}:${VERSION} ${IMAGE_NAME}:latest

echo "Built ${IMAGE_NAME}:${VERSION}"
```

#### `scripts/docker-run.sh`
```bash
#!/bin/bash
# Run Docker container

set -e

IMAGE_NAME="g-copilot-proxy"
CONTAINER_NAME="g-copilot-proxy-dev"

# Stop existing container
docker stop ${CONTAINER_NAME} 2>/dev/null || true
docker rm ${CONTAINER_NAME} 2>/dev/null || true

# Run new container
docker run -d \
    --name ${CONTAINER_NAME} \
    -p 8000:8000 \
    -v $(pwd)/../ai:/app/ai:ro \
    -e AUTH_MODE=passthrough \
    -e LOG_LEVEL=INFO \
    ${IMAGE_NAME}:latest

echo "Container started: ${CONTAINER_NAME}"
echo "Logs: docker logs -f ${CONTAINER_NAME}"
```

#### `scripts/deploy.sh`
```bash
#!/bin/bash
# Deploy to production

set -e

VERSION=${1:-$(date +%Y%m%d-%H%M%S)}
IMAGE_NAME="g-copilot-proxy"
REGISTRY="your-registry.com"

echo "Building for production..."
./scripts/docker-build.sh ${VERSION}

echo "Tagging for registry..."
docker tag ${IMAGE_NAME}:${VERSION} ${REGISTRY}/${IMAGE_NAME}:${VERSION}
docker tag ${IMAGE_NAME}:${VERSION} ${REGISTRY}/${IMAGE_NAME}:latest

echo "Pushing to registry..."
docker push ${REGISTRY}/${IMAGE_NAME}:${VERSION}
docker push ${REGISTRY}/${IMAGE_NAME}:latest

echo "Deployed version: ${VERSION}"
```

## Step 11: Create README

#### `README.md`
```markdown
# g-copilot-proxy

OpenAI & Anthropic compatible proxy server for GitHub Copilot.

## Features

- OpenAI-compatible `/v1/chat/completions` endpoint
- Anthropic-compatible `/v1/messages` endpoint
- Full SSE streaming support
- Model aliasing for easy model selection
- Pass-through and managed authentication modes
- Docker deployment ready

## Quick Start

### Local Development

```bash
# Install dependencies
poetry install

# Copy environment file
cp .env.example .env

# Start development server
./scripts/dev.sh

# Or with Poetry
poetry run uvicorn app.main:app --reload
```

### Docker

```bash
# Build image
docker build -t g-copilot-proxy .

# Run container
docker run -p 8000:8000 \
    -v $(pwd)/../ai:/app/ai:ro \
    -e AUTH_MODE=passthrough \
    g-copilot-proxy

# Or with docker-compose
docker-compose up
```

## Usage

### OpenAI SDK

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:8000/v1",
    api_key="your-github-copilot-token"
)

response = client.chat.completions.create(
    model="claude-sonnet-4.5",
    messages=[{"role": "user", "content": "Hello!"}]
)

print(response.choices[0].message.content)
```

### Anthropic SDK

```python
import anthropic

client = anthropic.Anthropic(
    base_url="http://localhost:8000/v1",
    api_key="your-github-copilot-token"
)

message = client.messages.create(
    model="claude-sonnet-4.5",
    max_tokens=1024,
    messages=[{"role": "user", "content": "Hello!"}]
)

print(message.content[0].text)
```

### cURL

```bash
# OpenAI format
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "model": "claude-sonnet-4.5",
    "messages": [{"role": "user", "content": "Hello!"}]
  }'

# Anthropic format
curl -X POST http://localhost:8000/v1/messages \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "model": "claude-sonnet-4.5",
    "max_tokens": 1024,
    "messages": [{"role": "user", "content": "Hello!"}]
  }'
```

## Available Models

Via GitHub Copilot:

| Model ID | Description |
|----------|-------------|
| `claude-haiku-4.5` | Claude Haiku 4.5 |
| `claude-sonnet-4` | Claude Sonnet 4 |
| `claude-sonnet-4.5` | Claude Sonnet 4.5 |
| `claude-opus-4.5` | Claude Opus 4.5 |
| `gpt-4.1` | GPT 4.1 |
| `gpt-4o` | GPT 4o |
| `gemini-2.5-pro` | Gemini 2.5 Pro |

Run `curl http://localhost:8000/v1/models` for the full list.

## Configuration

| Environment Variable | Default | Description |
|---------------------|---------|-------------|
| `AUTH_MODE` | `passthrough` | Authentication mode: `passthrough` or `managed` |
| `PIAI_MODULE_PATH` | `../ai` | Path to pi-ai Node.js module |
| `CORS_ORIGINS` | `["*"]` | CORS allowed origins |
| `LOG_LEVEL` | `INFO` | Logging level |

## Authentication

### Pass-Through Mode (Default)

Send your GitHub Copilot token in requests:

```bash
Authorization: Bearer your-github-copilot-token
```

### Managed Mode

Server handles OAuth. First, authenticate:

```bash
curl -X POST http://localhost:8000/auth/login
```

Then check status:

```bash
curl http://localhost:8000/auth/status
```

## Testing

```bash
# Run all tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=app

# Run E2E tests (requires valid credentials)
poetry run pytest --run-e2e
```

## Development

```bash
# Format code
poetry run black app/
poetry run ruff check --fix app/

# Type check
poetry run mypy app/
```

## License

MIT
```

## Running Tests

```bash
# Install dependencies
poetry install

# Run all tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=app --cov-report=html

# Run specific test file
poetry run pytest tests/test_openai_api.py

# Run E2E tests (requires real Copilot credentials)
poetry run pytest --run-e2e

# Run linters
poetry run ruff check app/
poetry run black --check app/
poetry run mypy app/
```

## Verification Checklist

- [ ] All unit tests pass
- [ ] API tests pass with mocked pi-ai
- [ ] Streaming responses work correctly
- [ ] Docker image builds successfully
- [ ] Docker container starts and serves requests
- [ ] Health check returns 200
- [ ] Metrics endpoint returns Prometheus data
- [ ] Nginx proxy configuration is valid
- [ ] SSL certificates are configured
- [ ] Environment variables are documented

## Next Steps

1. Set up CI/CD pipeline (GitHub Actions, GitLab CI, etc.)
2. Configure monitoring alerts (Prometheus Alertmanager)
3. Set up log aggregation (ELK stack, Loki, etc.)
4. Implement rate limiting per API key
5. Add request caching for identical prompts
6. Consider adding WebHook support for async responses
7. Set up automated backups of OAuth credentials

---

**Implementation Complete!** 🎉

The `g-copilot-proxy` is now fully implemented with testing, Docker deployment, and production-ready configuration.
