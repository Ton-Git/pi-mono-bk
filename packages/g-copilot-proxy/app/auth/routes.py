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

    import uuid
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
