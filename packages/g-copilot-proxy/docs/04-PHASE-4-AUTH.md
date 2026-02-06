# Phase 4: Authentication and Middleware

## Overview

Implement authentication layer supporting both pass-through (client provides GitHub Copilot token) and managed (server handles OAuth) modes.

> **IMPORTANT: No commits should be made during implementation.** This is a planning-only repository. All code changes should be made in the actual implementation package, not committed to git during the planning phase.

## Authentication Modes

### Pass-Through Mode (Default)
Client sends GitHub Copilot access token in request headers. Proxy forwards it to pi-ai library.

```
Client → Proxy (with Authorization: Bearer <copilot_token>) → pi-ai → GitHub Copilot
```

### Managed Mode
Server handles OAuth flow, stores credentials, and uses them for all requests.

```
Client → Proxy (no auth) → pi-ai (uses stored token) → GitHub Copilot
           (OAuth login via /auth endpoint)
```

## Step 1: Create Auth Configuration

#### `app/auth/config.py`
```python
"""Authentication configuration and utilities."""

import logging
from typing import Optional
from pathlib import Path
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class AuthConfig:
    """Authentication configuration."""

    def __init__(self):
        self.mode = settings.auth_mode
        self.api_key_header = settings.api_key_header
        self.api_key_prefix = settings.api_key_prefix
        self.credentials_path = Path(".copilot-auth.json")

    def is_pass_through(self) -> bool:
        """Check if running in pass-through mode."""
        return self.mode == "passthrough"

    def is_managed(self) -> bool:
        """Check if running in managed mode."""
        return self.mode == "managed"

    def get_stored_credentials(self) -> Optional[dict]:
        """Get stored OAuth credentials (managed mode only)."""
        if not self.credentials_path.exists():
            return None

        try:
            import json
            with open(self.credentials_path, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to read credentials: {e}")
            return None

    def save_credentials(self, credentials: dict) -> None:
        """Save OAuth credentials (managed mode only)."""
        try:
            import json
            with open(self.credentials_path, "w") as f:
                json.dump(credentials, f, indent=2)
            logger.info(f"Credentials saved to {self.credentials_path}")
        except Exception as e:
            logger.error(f"Failed to save credentials: {e}")
            raise

    def clear_credentials(self) -> None:
        """Clear stored credentials."""
        if self.credentials_path.exists():
            self.credentials_path.unlink()
            logger.info("Credentials cleared")


auth_config = AuthConfig()


def get_auth_config() -> AuthConfig:
    """Get auth config singleton."""
    return auth_config
```

## Step 2: Create GitHub Copilot OAuth Handler

#### `app/auth/github_copilot.py`
```python
"""GitHub Copilot OAuth handler for managed authentication mode."""

import asyncio
import json
import logging
from pathlib import Path
from typing import Optional, Callable

logger = logging.getLogger(__name__)


class GitHubCopilotOAuth:
    """Handler for GitHub Copilot OAuth flow."""

    def __init__(self, module_path: str = "../ai", node_path: str = "node"):
        self.module_path = Path(module_path).resolve()
        self.node_path = node_path

        # OAuth script template
        self.oauth_script = """
        const { loginGitHubCopilot } = require('@mariozechner/pi-ai');

        async function main() {
            try {
                const input = JSON.parse(require('fs').readFileSync(0, 'utf-8'));

                // For OAuth flow, we'll use the CLI's login mechanism
                const { login } = require('@mariozechner/pi-ai/cli');

                const credentials = await login('github-copilot', {
                    onAuth: (url, instructions) => {
                        console.log(JSON.stringify({
                            type: 'auth',
                            url: url,
                            instructions: instructions
                        }));
                    },
                    onPrompt: async (prompt) => {
                        // For automation, read from stdin
                        console.log(JSON.stringify({
                            type: 'prompt',
                            message: prompt.message
                        }));
                        return input.enterpriseUrl || '';
                    },
                    onProgress: (msg) => {
                        console.log(JSON.stringify({
                            type: 'progress',
                            message: msg
                        }));
                    }
                });

                console.log(JSON.stringify({
                    type: 'done',
                    credentials: credentials
                }));
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

    async def login(
        self,
        enterprise_url: Optional[str] = None,
        on_auth: Optional[Callable[[str, Optional[str]], None]] = None,
        on_progress: Optional[Callable[[str], None]] = None,
    ) -> dict:
        """
        Perform GitHub Copilot OAuth login.

        Args:
            enterprise_url: Optional GitHub Enterprise URL
            on_auth: Callback when auth URL is available
            on_progress: Callback for progress updates

        Returns:
            OAuth credentials dict with 'access', 'refresh', 'expires' keys
        """
        payload = {"enterpriseUrl": enterprise_url}

        cmd = [
            self.node_path,
            "--eval",
            self.oauth_script,
        ]

        logger.info("Starting GitHub Copilot OAuth flow...")

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
            process.stdin.write(input_data)
            await process.stdin.drain()
            process.stdin.close()

            credentials = None

            # Read and parse output line by line
            while True:
                line = await process.stdout.readline()
                if not line:
                    break

                line_str = line.decode("utf-8").strip()
                if not line_str:
                    continue

                try:
                    output = json.loads(line_str)
                    output_type = output.get("type")

                    if output_type == "auth":
                        url = output.get("url", "")
                        instructions = output.get("instructions")
                        if on_auth:
                            on_auth(url, instructions)
                        logger.info(f"Auth URL: {url}")
                        if instructions:
                            logger.info(f"Instructions: {instructions}")

                    elif output_type == "progress":
                        msg = output.get("message", "")
                        if on_progress:
                            on_progress(msg)
                        logger.info(f"Progress: {msg}")

                    elif output_type == "done":
                        credentials = output.get("credentials")
                        logger.info("OAuth login successful")
                        break

                    elif output_type == "error":
                        error_msg = output.get("error", "Unknown error")
                        logger.error(f"OAuth error: {error_msg}")
                        raise Exception(f"OAuth failed: {error_msg}")

                except json.JSONDecodeError:
                    logger.warning(f"Failed to parse OAuth output: {line_str}")
                    continue

            # Wait for process to complete
            returncode = await process.wait()

            if returncode != 0:
                stderr = await process.stderr.read()
                error_output = stderr.decode("utf-8")
                logger.error(f"OAuth subprocess failed: {error_output}")
                raise Exception(f"OAuth failed with return code {returncode}")

            if not credentials:
                raise Exception("OAuth completed but no credentials received")

            return credentials

        except asyncio.CancelledError:
            if process:
                process.kill()
                await process.wait()
            raise
        except Exception as e:
            logger.exception(f"OAuth login failed: {e}")
            raise

    async def refresh_token(self, refresh_token: str) -> dict:
        """
        Refresh an expired OAuth token.

        Args:
            refresh_token: The refresh token from previous credentials

        Returns:
            New credentials dict
        """
        refresh_script = """
        const { refreshGitHubCopilotToken } = require('@mariozechner/pi-ai');

        async function main() {
            try {
                const input = JSON.parse(require('fs').readFileSync(0, 'utf-8'));
                const credentials = await refreshGitHubCopilotToken(input.refreshToken);
                console.log(JSON.stringify({
                    type: 'done',
                    credentials: credentials
                }));
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

        payload = {"refreshToken": refresh_token}
        cmd = [self.node_path, "--eval", refresh_script]

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(self.module_path),
            )

            input_data = json.dumps(payload).encode("utf-8")
            process.stdin.write(input_data)
            await process.stdin.drain()
            process.stdin.close()

            stdout, _ = await process.communicate()

            if process.returncode != 0:
                raise Exception("Token refresh failed")

            output = json.loads(stdout.decode("utf-8"))
            if output.get("type") == "done":
                return output.get("credentials", {})
            else:
                raise Exception(output.get("error", "Token refresh failed"))

        except Exception as e:
            logger.exception(f"Token refresh failed: {e}")
            raise


oauth_handler = GitHubCopilotOAuth()


def get_oauth_handler() -> GitHubCopilotOAuth:
    """Get OAuth handler singleton."""
    return oauth_handler
```

## Step 3: Create Authentication Middleware

#### `app/auth/middleware.py`
```python
"""Authentication middleware."""

import logging
from typing import Optional
from fastapi import Request, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.auth.config import get_auth_config

logger = logging.getLogger(__name__)
security = HTTPBearer(auto_error=False)


async def get_api_key(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = None,
) -> Optional[str]:
    """
    Extract API key from request based on auth mode.

    In pass-through mode: Returns the client-provided API key
    In managed mode: Returns the stored OAuth credentials access token
    """
    config = get_auth_config()

    if config.is_pass_through():
        # Pass-through: use client's API key
        if credentials is None:
            # Try to get from header directly
            auth_header = request.headers.get(config.api_key_header)
            if not auth_header:
                return None

            if auth_header.startswith(config.api_key_prefix):
                return auth_header[len(config.api_key_prefix):]
            return auth_header

        return credentials.credentials

    elif config.is_managed():
        # Managed: use stored credentials
        stored_creds = config.get_stored_credentials()
        if not stored_creds:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="No OAuth credentials found. Please authenticate at /auth/login",
            )

        access_token = stored_creds.get("access")
        if not access_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid stored credentials. Please re-authenticate at /auth/login",
            )

        # Check if token is expired
        expires = stored_creds.get("expires")
        if expires:
            import time
            if time.time() * 1000 > expires:
                # Token expired, try to refresh
                refresh_token = stored_creds.get("refresh")
                if refresh_token:
                    try:
                        from app.auth.github_copilot import get_oauth_handler
                        oauth = get_oauth_handler()
                        new_creds = await oauth.refresh_token(refresh_token)

                        # Update stored credentials
                        new_creds["refresh"] = refresh_token  # Keep original refresh token
                        config.save_credentials(new_creds)

                        return new_creds.get("access")
                    except Exception as e:
                        logger.error(f"Token refresh failed: {e}")
                        raise HTTPException(
                            status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Token expired and refresh failed. Please re-authenticate at /auth/login",
                        )
                else:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Token expired. Please re-authenticate at /auth/login",
                    )

        return access_token

    return None


async def optional_auth(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = None,
) -> Optional[str]:
    """
    Optional authentication - returns API key if available, None otherwise.
    Used for endpoints that work with or without auth.
    """
    try:
        return await get_api_key(request, credentials)
    except HTTPException:
        return None
```

## Step 4: Create Auth Endpoints

#### `app/auth/routes.py`
```python
"""Authentication endpoints."""

import logging
from typing import Optional
from fastapi import APIRouter, Request, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field

from app.auth.config import get_auth_config
from app.auth.github_copilot import get_oauth_handler

logger = logging.getLogger(__name__)
router = APIRouter()


class LoginRequest(BaseModel):
    """OAuth login request."""
    enterprise_url: Optional[str] = Field(None, description="GitHub Enterprise URL")


class LoginResponse(BaseModel):
    """OAuth login response."""
    status: str
    message: str


class StatusResponse(BaseModel):
    """Auth status response."""
    mode: str
    authenticated: bool
    enterprise_url: Optional[str] = None


class LogoutResponse(BaseModel):
    """Logout response."""
    status: str
    message: str


# Store pending OAuth URLs for polling
_pending_oauth: dict[str, dict] = {}


@router.post("/login", response_model=LoginResponse)
async def login_oauth(request: Request, login_req: LoginRequest, background_tasks: BackgroundTasks):
    """
    Initiate GitHub Copilot OAuth login.

    In managed mode, this starts the OAuth flow. The client should poll
    /auth/status to check when login is complete.

    In pass-through mode, this returns an error since OAuth is not used.
    """
    config = get_auth_config()

    if config.is_pass_through():
        raise HTTPException(
            status_code=400,
            detail="OAuth login not available in pass-through mode. "
                   "Send your GitHub Copilot token in the Authorization header.",
        )

    # Start OAuth in background
    async def do_oauth():
        oauth = get_oauth_handler()

        session_id = None

        try:
            import uuid
            session_id = str(uuid.uuid4())

            def on_auth(url: str, instructions: Optional[str]):
                _pending_oauth[session_id] = {
                    "status": "pending",
                    "url": url,
                    "instructions": instructions,
                }

            def on_progress(msg: str):
                if session_id in _pending_oauth:
                    _pending_oauth[session_id]["message"] = msg

            credentials = await oauth.login(
                enterprise_url=login_req.enterprise_url,
                on_auth=on_auth,
                on_progress=on_progress,
            )

            # Save credentials
            config.save_credentials(credentials)

            # Update status
            if session_id in _pending_oauth:
                _pending_oauth[session_id]["status"] = "complete"

        except Exception as e:
            logger.error(f"OAuth failed: {e}")
            if session_id and session_id in _pending_oauth:
                _pending_oauth[session_id] = {
                    "status": "error",
                    "error": str(e),
                }

    background_tasks.add_task(do_oauth)

    return LoginResponse(
        status="started",
        message="OAuth flow initiated. Poll /auth/status to check completion.",
    )


@router.get("/status", response_model=StatusResponse)
async def get_auth_status(request: Request):
    """
    Get authentication status.

    Returns the current auth mode and whether credentials are available.
    """
    config = get_auth_config()

    stored_creds = config.get_stored_credentials()
    authenticated = stored_creds is not None

    enterprise_url = None
    if stored_creds:
        enterprise_url = stored_creds.get("enterpriseUrl")

    return StatusResponse(
        mode=config.mode,
        authenticated=authenticated,
        enterprise_url=enterprise_url,
    )


@router.post("/logout", response_model=LogoutResponse)
async def logout(request: Request):
    """
    Clear stored OAuth credentials.

    Only applicable in managed mode.
    """
    config = get_auth_config()

    if config.is_pass_through():
        raise HTTPException(
            status_code=400,
            detail="Logout not applicable in pass-through mode.",
        )

    config.clear_credentials()

    return LogoutResponse(
        status="success",
        message="Credentials cleared",
    )


@router.get("/config")
async def get_auth_config_info(request: Request):
    """
    Get current authentication configuration.

    Returns the auth mode and related settings.
    """
    config = get_auth_config()

    return {
        "mode": config.mode,
        "api_key_header": config.api_key_header,
        "api_key_prefix": config.api_key_prefix,
    }
```

#### `app/auth/__init__.py`
```python
"""Authentication utilities."""

from app.auth.config import get_auth_config, AuthConfig
from app.auth.github_copilot import get_oauth_handler, GitHubCopilotOAuth
from app.auth.middleware import get_api_key, optional_auth

__all__ = [
    "get_auth_config",
    "AuthConfig",
    "get_oauth_handler",
    "GitHubCopilotOAuth",
    "get_api_key",
    "optional_auth",
]
```

## Step 5: Update Main App

#### `app/main.py` (update)
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
from app.auth import routes as auth_routes
import logging

settings = get_settings()
logging.basicConfig(level=settings.log_level)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")

    # Log authentication mode
    from app.auth.config import get_auth_config
    auth_config = get_auth_config()
    logger.info(f"Authentication mode: {auth_config.mode}")

    if auth_config.is_managed():
        stored_creds = auth_config.get_stored_credentials()
        if stored_creds:
            logger.info("Loaded stored OAuth credentials")
        else:
            logger.warning("No OAuth credentials found. Use /auth/login to authenticate")

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

    # Register auth routes
    app.include_router(auth_routes.router, prefix="/auth", tags=["authentication"])

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
            "authentication": settings.auth_mode,
        }

    return app


app = create_app()
```

## Step 6: Update Chat Endpoints to Use Auth Middleware

#### `app/api/openai/chat.py` (update imports and function)
```python
# Add imports at the top of the file
from fastapi import Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.auth import get_api_key

# Update create_chat_completion function signature
@router.post("/chat/completions", response_model=None)
async def create_chat_completion(
    request: ChatCompletionRequest,
    req: Request,
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer(auto_error=False)),
):
    """
    Create a chat completion (OpenAI-compatible).

    Supports both streaming and non-streaming modes.
    """
    api_key = await get_api_key(req, credentials)

    if request.stream:
        return await stream_chat_completion(request, api_key)
    else:
        return await create_non_streaming_completion(request, api_key)
```

## Environment Configuration

Update `.env.example` with auth options:

```bash
# Authentication Mode
# passthrough: Client sends GitHub Copilot token in Authorization header
# managed: Server handles OAuth flow and stores credentials
AUTH_MODE=passthrough
```

## Verification

Test authentication endpoints:

```bash
# In pass-through mode (default)
curl http://localhost:8000/auth/config
# Returns: {"mode":"passthrough",...}

curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_COPILOT_TOKEN" \
  -d '{"model":"claude-sonnet-4.5","messages":[{"role":"user","content":"Hi"}]}'

# In managed mode
export AUTH_MODE=managed
poetry run uvicorn app.main:app --reload

# Check status
curl http://localhost:8000/auth/status
# Returns: {"mode":"managed","authenticated":false}

# Initiate OAuth (this will open a browser in interactive mode)
# For production, you'd want a web-based flow
```

## Next Steps

Proceed to [Phase 5: Testing & Deployment](./05-PHASE-5-TESTING.md) for testing, Docker setup, and deployment.
