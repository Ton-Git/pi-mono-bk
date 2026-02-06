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
