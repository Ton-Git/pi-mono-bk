"""OpenAI-compatible API routes."""

from fastapi import APIRouter
from app.api.openai import chat, models_endpoint

router = APIRouter()

# Include all OpenAI routes
router.include_router(chat.router, tags=["chat"])
router.include_router(models_endpoint.router, tags=["models"])
