"""Anthropic-compatible models endpoint."""

import logging
from fastapi import APIRouter

from app.api.anthropic.models import ModelsListResponse
from app.core import PiAIBridgeError, get_piai_bridge, AnthropicMapper

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/models", response_model=ModelsListResponse)
async def list_models():
    """
    List available models (Anthropic-compatible).

    Returns all GitHub Copilot models available through pi-ai.
    """
    bridge = get_piai_bridge()

    try:
        piai_models = await bridge.get_models()

        anthropic_models = [
            AnthropicMapper.map_piai_model_to_anthropic(m) for m in piai_models
        ]

        return ModelsListResponse(data=anthropic_models, has_more=False)

    except PiAIBridgeError as e:
        logger.error(f"pi-ai bridge error: {e.message}")
        # Return empty list on error
        return ModelsListResponse(data=[], has_more=False)

    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        return ModelsListResponse(data=[], has_more=False)
