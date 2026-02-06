"""OpenAI-compatible models endpoint."""

import logging
from fastapi import APIRouter

from app.api.openai.models import ModelsListResponse
from app.core import PiAIBridgeError, get_piai_bridge, OpenAIMapper

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/models", response_model=ModelsListResponse)
async def list_models():
    """
    List available models (OpenAI-compatible).

    Returns all GitHub Copilot models available through pi-ai.
    """
    bridge = get_piai_bridge()

    try:
        piai_models = await bridge.get_models()

        openai_models = [
            OpenAIMapper.map_piai_model_to_openai(m) for m in piai_models
        ]

        return ModelsListResponse(object="list", data=openai_models)

    except PiAIBridgeError as e:
        logger.error(f"pi-ai bridge error: {e.message}")
        # Return empty list on error
        return ModelsListResponse(object="list", data=[])

    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        return ModelsListResponse(object="list", data=[])


@router.get("/models/{model_id}", response_model=dict)
async def get_model(model_id: str):
    """
    Get a specific model by ID (OpenAI-compatible).

    Note: This is not part of the standard OpenAI API but included for convenience.
    """
    bridge = get_piai_bridge()

    try:
        piai_models = await bridge.get_models()

        for model in piai_models:
            if model.get("id") == model_id:
                return OpenAIMapper.map_piai_model_to_openai(model)

        return {"error": "Model not found"}

    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        return {"error": "Internal server error"}
