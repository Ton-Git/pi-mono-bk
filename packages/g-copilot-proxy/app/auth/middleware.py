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
                        # For now, just log the expired token
                        logger.warning("OAuth token expired but refresh not implemented")
                        raise HTTPException(
                            status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Token expired. Please re-authenticate at /auth/login",
                        )
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
