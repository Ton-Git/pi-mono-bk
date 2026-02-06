"""Anthropic-compatible API routes."""

from fastapi import APIRouter
from app.api.anthropic import messages, models_endpoint

router = APIRouter()

# Include all Anthropic routes
router.include_router(messages.router, tags=["messages"])
router.include_router(models_endpoint.router, tags=["models"])
