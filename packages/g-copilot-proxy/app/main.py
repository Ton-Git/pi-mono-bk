"""FastAPI application entry point."""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import get_settings
from app.api.openai import router as openai_router
from app.api.anthropic import router as anthropic_router
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
    app.include_router(openai_router, prefix="/v1", tags=["openai"])

    # Register Anthropic-compatible routes
    app.include_router(anthropic_router, prefix="/v1", tags=["anthropic"])

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
