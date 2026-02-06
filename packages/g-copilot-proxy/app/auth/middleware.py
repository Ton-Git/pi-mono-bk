"""Authentication middleware."""

import logging
import time
from typing import Optional
from fastapi import Request, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.auth.config import get_auth_config

logger = logging.getLogger(__name__)
security = HTTPBearer(auto_error=False)


async def get_api_key(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = None,
) -> str:
    """
    Get API key from stored OAuth credentials.

    GitHub Copilot requires OAuth device flow authentication.
    Personal access tokens are not supported.

    Raises HTTPException if credentials are not found or expired.
    """
    config = get_auth_config()
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
        if time.time() * 1000 > expires:
            logger.warning("OAuth token expired. Please re-authenticate at /auth/login")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token expired. Please re-authenticate at /auth/login",
            )

    return access_token


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
