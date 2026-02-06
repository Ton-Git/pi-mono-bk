# Phase 1: Project Setup and Basic Structure

## Overview

Set up the Python project structure, dependencies, and base configuration for `g-copilot-proxy`.

> **IMPORTANT: No commits should be made during implementation.** This is a planning-only repository. All code changes should be made in the actual implementation package, not committed to git during the planning phase.

## Step 1: Create Project Structure

```bash
# Create directory structure
cd /workspaces/pi-mono-bk/packages/g-copilot-proxy

mkdir -p app/api/openai
mkdir -p app/api/anthropic
mkdir -p app/core
mkdir -p app/auth
mkdir -p tests
mkdir -p scripts
```

### Create Base Files

#### `app/__init__.py`
```python
"""g-copilot-proxy: OpenAI & Anthropic compatible proxy for GitHub Copilot."""

__version__ = "0.1.0"
```

#### `app/config.py`
```python
"""Configuration settings for g-copilot-proxy."""

from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Server settings
    app_name: str = "g-copilot-proxy"
    app_version: str = "0.1.0"
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False

    # pi-ai bridge settings
    piai_module_path: str = "../ai"  # Path to @mariozechner/pi-ai
    piai_node_path: str = "node"  # Path to Node.js executable

    # GitHub Copilot settings
    copilot_base_url: str = "https://api.individual.githubcopilot.com"
    copilot_enterprise_url: Optional[str] = None

    # Authentication settings
    auth_mode: str = "passthrough"  # "passthrough" or "managed"
    api_key_header: str = "Authorization"
    api_key_prefix: str = "Bearer "

    # CORS settings
    cors_origins: list[str] = ["*"]
    cors_allow_credentials: bool = True
    cors_allow_methods: list[str] = ["*"]
    cors_allow_headers: list[str] = ["*"]

    # Rate limiting
    rate_limit_requests: int = 100
    rate_limit_period: int = 60  # seconds

    # Logging
    log_level: str = "INFO"

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
```

#### `app/main.py`
```python
"""FastAPI application entry point."""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import get_settings
from app.api.openai import chat as openai_chat
from app.api.openai import models as openai_models
from app.api.anthropic import messages as anthropic_messages
from app.api.anthropic import models as anthropic_models
import logging

settings = get_settings()
logging.basicConfig(level=settings.log_level)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    yield
    logger.info(f"Shutting down {settings.app_name}")


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="OpenAI & Anthropic compatible proxy for GitHub Copilot",
        lifespan=lifespan,
    )

    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=settings.cors_allow_credentials,
        allow_methods=settings.cors_allow_methods,
        allow_headers=settings.cors_allow_headers,
    )

    # Register OpenAI-compatible routes
    app.include_router(openai_chat.router, prefix="/v1", tags=["openai"])
    app.include_router(openai_models.router, prefix="/v1", tags=["openai"])

    # Register Anthropic-compatible routes
    app.include_router(anthropic_messages.router, prefix="/v1", tags=["anthropic"])
    app.include_router(anthropic_models.router, prefix="/v1", tags=["anthropic"])

    # Health check
    @app.get("/health")
    async def health_check():
        return {"status": "healthy", "version": settings.app_version}

    # Root endpoint
    @app.get("/")
    async def root():
        return {
            "name": settings.app_name,
            "version": settings.app_version,
            "docs": "/docs",
            "openapi": "/openapi.json",
        }

    return app


app = create_app()
```

## Step 2: Create pyproject.toml

#### `pyproject.toml`
```toml
[tool.poetry]
name = "g-copilot-proxy"
version = "0.1.0"
description = "OpenAI & Anthropic compatible proxy for GitHub Copilot"
authors = ["Your Name <you@example.com>"]
readme = "README.md"
packages = [{include = "app"}]

[tool.poetry.dependencies]
python = "^3.11"
fastapi = "^0.115.0"
uvicorn = {extras = ["standard"], version = "^0.32.0"}
pydantic = "^2.10.0"
pydantic-settings = "^2.6.0"
httpx = "^0.28.0"
python-multipart = "^0.0.12"
sse-starlette = "^2.1.0"
python-dotenv = "^1.0.0"

[tool.poetry.group.dev.dependencies]
pytest = "^8.3.0"
pytest-asyncio = "^0.24.0"
pytest-cov = "^6.0.0"
black = "^24.10.0"
ruff = "^0.8.0"
mypy = "^1.13.0"

[build-system]
requires = ["poetry-core"]
build-backend = "poetry.core.masonry.api"

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W", "UP"]
ignore = ["E501"]

[tool.black]
line-length = 100
target-version = ['py311']

[tool.mypy]
python_version = "3.11"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

## Step 3: Create Core Bridge Module

The bridge module handles communication with the Node.js `@mariozechner/pi-ai` library.

#### `app/core/piai_bridge.py`
```python
"""Bridge to @mariozechner/pi-ai Node.js library."""

import asyncio
import json
import logging
from pathlib import Path
from typing import Any, Optional
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Node.js script template for streaming responses
PIAI_STREAM_SCRIPT = """
const { getModel, stream } = require('@mariozechner/pi-ai');

async function main() {
    try {
        const input = JSON.parse(require('fs').readFileSync(0, 'utf-8'));
        const model = getModel('github-copilot', input.model);
        const context = input.context;

        // Add API key if provided
        const options = input.apiKey ? { apiKey: input.apiKey } : {};
        if (input.temperature !== undefined) options.temperature = input.temperature;
        if (input.maxTokens !== undefined) options.maxTokens = input.maxTokens;

        const s = stream(model, context, options);

        for await (const event of s) {
            console.log(JSON.stringify(event));
        }
    } catch (error) {
        console.error(JSON.stringify({
            type: 'error',
            error: error.message || String(error)
        }));
        process.exit(1);
    }
}

main();
"""

# Node.js script for getting available models
PIAI_MODELS_SCRIPT = """
const { getModels } = require('@mariozechner/pi-ai');

try {
    const models = getModels('github-copilot');
    console.log(JSON.stringify(models));
} catch (error) {
    console.error(JSON.stringify({
        type: 'error',
        error: error.message || String(error)
    }));
    process.exit(1);
}
"""


class PiAIBridgeError(Exception):
    """Exception raised when pi-ai bridge encounters an error."""

    def __init__(self, message: str, details: Optional[dict] = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class PiAIBridge:
    """Bridge to @mariozechner/pi-ai library via Node.js subprocess."""

    def __init__(
        self,
        module_path: Optional[str] = None,
        node_path: Optional[str] = None,
    ):
        """
        Initialize the pi-ai bridge.

        Args:
            module_path: Path to the pi-ai Node.js module
            node_path: Path to Node.js executable
        """
        self.module_path = Path(module_path or settings.piai_module_path).resolve()
        self.node_path = node_path or settings.piai_node_path

        if not self.module_path.exists():
            raise PiAIBridgeError(
                f"pi-ai module not found at {self.module_path}",
                {"module_path": str(self.module_path)},
            )

    async def stream_completion(
        self,
        model: str,
        messages: list[dict],
        api_key: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        tools: Optional[list[dict]] = None,
        system_prompt: Optional[str] = None,
    ) -> Any:
        """
        Stream completion from pi-ai.

        Args:
            model: Model identifier (e.g., 'claude-sonnet-4.5')
            messages: List of message dictionaries
            api_key: Optional API key for authentication
            temperature: Optional temperature setting
            max_tokens: Optional max tokens setting
            tools: Optional list of tool definitions
            system_prompt: Optional system prompt

        Yields:
            Streaming events from pi-ai

        Raises:
            PiAIBridgeError: If the subprocess fails
        """
        payload = {
            "model": model,
            "context": {
                "messages": messages,
                "tools": tools or [],
            },
        }

        if system_prompt:
            payload["context"]["systemPrompt"] = system_prompt
        if api_key:
            payload["apiKey"] = api_key
        if temperature is not None:
            payload["temperature"] = temperature
        if max_tokens is not None:
            payload["maxTokens"] = max_tokens

        cmd = [
            self.node_path,
            "--eval",
            PIAI_STREAM_SCRIPT,
        ]

        logger.debug(f"Running pi-ai command: {' '.join(cmd)}")

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(self.module_path),
            )

            # Send payload to stdin
            input_data = json.dumps(payload).encode("utf-8")
            _, stderr = await process.communicate(input_data)

            if process.returncode != 0:
                error_output = stderr.decode("utf-8")
                logger.error(f"pi-ai subprocess failed: {error_output}")
                raise PiAIBridgeError(
                    "pi-ai subprocess failed",
                    {"returncode": process.returncode, "stderr": error_output},
                )

        except asyncio.CancelledError:
            if process:
                process.kill()
            raise
        except Exception as e:
            raise PiAIBridgeError(
                f"Failed to execute pi-ai: {str(e)}",
                {"exception": str(e)},
            )

    async def get_models(self) -> list[dict]:
        """
        Get available models from pi-ai.

        Returns:
            List of model dictionaries

        Raises:
            PiAIBridgeError: If the subprocess fails
        """
        cmd = [
            self.node_path,
            "--eval",
            PIAI_MODELS_SCRIPT,
        ]

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(self.module_path),
            )

            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                error_output = stderr.decode("utf-8")
                logger.error(f"pi-ai get_models failed: {error_output}")
                raise PiAIBridgeError(
                    "Failed to get models from pi-ai",
                    {"returncode": process.returncode, "stderr": error_output},
                )

            return json.loads(stdout.decode("utf-8"))

        except Exception as e:
            raise PiAIBridgeError(
                f"Failed to execute pi-ai get_models: {str(e)}",
                {"exception": str(e)},
            )

    async def stream_completion_iter(
        self,
        model: str,
        messages: list[dict],
        api_key: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        tools: Optional[list[dict]] = None,
        system_prompt: Optional[str] = None,
    ) -> Any:
        """
        Stream completion from pi-ai, yielding events line by line.

        This is an async generator that yields events as they arrive.
        """
        payload = {
            "model": model,
            "context": {
                "messages": messages,
                "tools": tools or [],
            },
        }

        if system_prompt:
            payload["context"]["systemPrompt"] = system_prompt
        if api_key:
            payload["apiKey"] = api_key
        if temperature is not None:
            payload["temperature"] = temperature
        if max_tokens is not None:
            payload["maxTokens"] = max_tokens

        cmd = [
            self.node_path,
            "--eval",
            PIAI_STREAM_SCRIPT,
        ]

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(self.module_path),
        )

        # Write payload and close stdin
        input_data = json.dumps(payload).encode("utf-8")
        process.stdin.write(input_data)
        await process.stdin.drain()
        process.stdin.close()

        try:
            # Read and parse output line by line
            while True:
                line = await process.stdout.readline()
                if not line:
                    break

                line_str = line.decode("utf-8").strip()
                if not line_str:
                    continue

                try:
                    event = json.loads(line_str)
                    yield event
                except json.JSONDecodeError:
                    logger.warning(f"Failed to parse pi-ai output: {line_str}")
                    continue

            # Wait for process to complete
            returncode = await process.wait()

            if returncode != 0:
                stderr = await process.stderr.read()
                error_output = stderr.decode("utf-8")
                logger.error(f"pi-ai subprocess failed: {error_output}")

        except asyncio.CancelledError:
            process.kill()
            await process.wait()
            raise
        finally:
            if process.returncode is None:
                process.kill()
                await process.wait()


# Singleton instance
_bridge_instance: Optional[PiAIBridge] = None


def get_piai_bridge() -> PiAIBridge:
    """Get or create the singleton pi-ai bridge instance."""
    global _bridge_instance
    if _bridge_instance is None:
        _bridge_instance = PiAIBridge()
    return _bridge_instance
```

#### `app/core/__init__.py`
```python
"""Core utilities for g-copilot-proxy."""

from app.core.piai_bridge import PiAIBridge, PiAIBridgeError, get_piai_bridge

__all__ = ["PiAIBridge", "PiAIBridgeError", "get_piai_bridge"]
```

## Step 4: Create Placeholder Route Files

Create placeholder files for routes to be implemented in later phases.

#### `app/api/__init__.py`
```python
"""API routes for g-copilot-proxy."""
```

#### `app/api/openai/__init__.py`
```python
"""OpenAI-compatible API routes."""
```

#### `app/api/openai/chat.py`
```python
"""OpenAI-compatible chat completions endpoint.

To be implemented in Phase 2.
"""

from fastapi import APIRouter

router = APIRouter()

@router.post("/chat/completions")
async def create_chat_completion():
    """Create a chat completion (OpenAI-compatible)."""
    return {"error": "Not implemented yet"}
```

#### `app/api/openai/models.py`
```python
"""OpenAI-compatible models endpoint.

To be implemented in Phase 2.
"""

from fastapi import APIRouter

router = APIRouter()

@router.get("/models")
async def list_models():
    """List available models (OpenAI-compatible)."""
    return {"object": "list", "data": []}
```

#### `app/api/anthropic/__init__.py`
```python
"""Anthropic-compatible API routes."""
```

#### `app/api/anthropic/messages.py`
```python
"""Anthropic-compatible messages endpoint.

To be implemented in Phase 3.
"""

from fastapi import APIRouter

router = APIRouter()

@router.post("/messages")
async def create_message():
    """Create a message (Anthropic-compatible)."""
    return {"error": "Not implemented yet"}
```

#### `app/api/anthropic/models.py`
```python
"""Anthropic-compatible models endpoint.

To be implemented in Phase 3.
"""

from fastapi import APIRouter

router = APIRouter()

@router.get("/models")
async def list_models():
    """List available models (Anthropic-compatible)."""
    return {"data": [], "has_more": False}
```

## Step 5: Environment and Helper Files

#### `.env.example`
```bash
# Server Configuration
APP_NAME=g-copilot-proxy
APP_VERSION=0.1.0
HOST=0.0.0.0
PORT=8000
DEBUG=false

# pi-ai Bridge
PIAI_MODULE_PATH=../ai
PIAI_NODE_PATH=node

# GitHub Copilot
COPILOT_BASE_URL=https://api.individual.githubcopilot.com
COPILOT_ENTERPRISE_URL=

# Authentication
AUTH_MODE=passthrough
API_KEY_HEADER=Authorization
API_KEY_PREFIX=Bearer

# CORS
CORS_ORIGINS=["*"]
CORS_ALLOW_CREDENTIALS=true

# Rate Limiting
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_PERIOD=60

# Logging
LOG_LEVEL=INFO
```

#### `scripts/dev.sh`
```bash
#!/bin/bash
# Development server startup script

cd "$(dirname "$0")/.."

# Activate virtual environment if using poetry
if command -v poetry &> /dev/null; then
    echo "Starting with Poetry..."
    poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
else
    echo "Starting with uvicorn..."
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
fi
```

#### `scripts/setup_oauth.js`
```javascript
// Helper script to set up GitHub Copilot OAuth
// Run with: node scripts/setup_oauth.js

const { loginGitHubCopilot } = require('@mariozechner/pi-ai');
const fs = require('fs');
const path = require('path');
const readline = require('readline');

const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout
});

function question(prompt) {
    return new Promise((resolve) => {
        rl.question(prompt, resolve);
    });
}

async function main() {
    console.log('GitHub Copilot OAuth Setup\n');

    const credentials = await loginGitHubCopilot({
        onAuth: (url, instructions) => {
            console.log('\nOpen this URL in your browser:');
            console.log(url);
            if (instructions) {
                console.log('\n' + instructions);
            }
        },
        onPrompt: async (prompt) => {
            return await question('\n' + prompt.message + ': ');
        },
        onProgress: (msg) => {
            console.log('\n' + msg);
        }
    });

    const authPath = path.join(__dirname, '..', '.copilot-auth.json');
    fs.writeFileSync(authPath, JSON.stringify(credentials, null, 2));

    console.log('\n✓ OAuth credentials saved to:', authPath);
    console.log('✓ You can now use the proxy with GitHub Copilot!\n');

    rl.close();
}

main().catch(console.error);
```

## Step 6: Initialize and Install

```bash
# Initialize git
git init

# Install dependencies with Poetry
poetry install

# Or with pip
pip install fastapi uvicorn pydantic pydantic-settings httpx python-multipart sse-starlette python-dotenv

# Create .env from example
cp .env.example .env

# Make dev script executable
chmod +x scripts/dev.sh
```

## Verification

Run the server to verify the setup:

```bash
# Start the development server
./scripts/dev.sh

# Or manually
poetry run uvicorn app.main:app --reload
```

Visit http://localhost:8000/docs to see the API documentation.

## Next Steps

Proceed to [Phase 2: OpenAI Endpoints](./02-PHASE-2-OPENAI.md) to implement the OpenAI-compatible API.
