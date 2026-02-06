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
