"""OpenAI-compatible chat completions endpoint."""

import logging
import time
import uuid
from typing import Optional
from fastapi import APIRouter, Request, HTTPException, Header
from fastapi.responses import StreamingResponse
from sse_starlette.sse import EventSourceResponse

from app.api.openai.models import (
    ChatCompletionRequest,
    ChatCompletionResponse,
)
from app.core import PiAIBridgeError, get_piai_bridge, OpenAIMapper

logger = logging.getLogger(__name__)
router = APIRouter()

# Default model if none specified
DEFAULT_MODEL = "claude-sonnet-4.5"

# Model alias mapping (OpenAI names -> GitHub Copilot names)
MODEL_ALIASES = {
    # GPT aliases
    "gpt-4": "gpt-4.1",
    "gpt-4-turbo": "gpt-4o",
    "gpt-3.5-turbo": "gpt-4.1",

    # Claude aliases
    "claude-3-haiku": "claude-haiku-4.5",
    "claude-3-sonnet": "claude-sonnet-4",
    "claude-3-opus": "claude-opus-4.5",
    "claude-3.5-sonnet": "claude-sonnet-4.5",

    # Generic aliases
    "default": DEFAULT_MODEL,
}


async def get_api_key(authorization: Optional[str] = None) -> Optional[str]:
    """Extract API key from Authorization header."""
    if not authorization:
        return None

    if authorization.startswith("Bearer "):
        return authorization[7:]

    # Allow raw token (no Bearer prefix)
    return authorization


def resolve_model(model: str) -> str:
    """Resolve model alias to actual GitHub Copilot model ID."""
    return MODEL_ALIASES.get(model, model)


async def stream_chat_completion(
    request: ChatCompletionRequest,
    api_key: Optional[str],
) -> StreamingResponse:
    """Stream chat completion from pi-ai."""
    bridge = get_piai_bridge()
    request_id = f"chatcmpl-{uuid.uuid4().hex[:24]}"
    created = int(time.time())
    model = resolve_model(request.model)

    # Convert OpenAI format to pi-ai format
    openai_messages = [msg.model_dump() for msg in request.messages]
    piai_messages, system_prompt = OpenAIMapper.map_openai_to_piai_messages(
        openai_messages,
    )

    piai_tools = None
    if request.tools:
        openai_tools = [t.model_dump() for t in request.tools]
        piai_tools = OpenAIMapper.map_openai_tools_to_piai(openai_tools)

    logger.info(f"Streaming chat completion: model={model}, messages={len(piai_messages)}")

    async def event_generator():
        """Generate SSE events from pi-ai stream."""
        try:
            async for event in bridge.stream_completion_iter(
                model=model,
                messages=piai_messages,
                api_key=api_key,
                temperature=request.temperature,
                max_tokens=request.max_tokens,
                tools=piai_tools,
                system_prompt=system_prompt,
            ):
                chunk = OpenAIMapper.map_piai_event_to_openai_chunk(
                    event,
                    request_id,
                    model,
                    created,
                )

                if chunk:
                    yield {"data": chunk}

                # Send final event on done
                if event.get("type") == "done":
                    yield {"data": "[DONE]"}

        except PiAIBridgeError as e:
            logger.error(f"pi-ai bridge error: {e.message}")
            # Send error as SSE event
            yield {
                "data": {
                    "id": request_id,
                    "object": "chat.completion.chunk",
                    "created": created,
                    "model": model,
                    "choices": [{
                        "index": 0,
                        "delta": {},
                        "finish_reason": "error",
                    }],
                }
            }
        except Exception as e:
            logger.exception(f"Unexpected error in stream: {e}")
            yield {
                "data": {
                    "id": request_id,
                    "object": "chat.completion.chunk",
                    "created": created,
                    "model": model,
                    "choices": [{
                        "index": 0,
                        "delta": {},
                        "finish_reason": "error",
                    }],
                }
            }

    return EventSourceResponse(event_generator())


async def create_non_streaming_completion(
    request: ChatCompletionRequest,
    api_key: Optional[str],
) -> ChatCompletionResponse:
    """Create non-streaming chat completion."""
    bridge = get_piai_bridge()
    request_id = f"chatcmpl-{uuid.uuid4().hex[:24]}"
    created = int(time.time())
    model = resolve_model(request.model)

    # Convert OpenAI format to pi-ai format
    openai_messages = [msg.model_dump() for msg in request.messages]
    piai_messages, system_prompt = OpenAIMapper.map_openai_to_piai_messages(
        openai_messages,
    )

    piai_tools = None
    if request.tools:
        openai_tools = [t.model_dump() for t in request.tools]
        piai_tools = OpenAIMapper.map_openai_tools_to_piai(openai_tools)

    logger.info(f"Creating chat completion: model={model}, messages={len(piai_messages)}")

    try:
        # Collect all events from the stream
        final_message = None
        async for event in bridge.stream_completion_iter(
            model=model,
            messages=piai_messages,
            api_key=api_key,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            tools=piai_tools,
            system_prompt=system_prompt,
        ):
            if event.get("type") == "done":
                final_message = event.get("message", {})
                break

        if not final_message:
            raise HTTPException(
                status_code=500,
                detail="Failed to get completion from pi-ai",
            )

        response_data = OpenAIMapper.map_piai_message_to_openai(
            final_message,
            request_id,
            model,
            created,
        )

        return ChatCompletionResponse(**response_data)

    except PiAIBridgeError as e:
        logger.error(f"pi-ai bridge error: {e.message}")
        raise HTTPException(
            status_code=500,
            detail=f"pi-ai bridge error: {e.message}",
        )
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}",
        )


@router.post("/chat/completions", response_model=None)
async def create_chat_completion(
    request: ChatCompletionRequest,
    req: Request,
    authorization: Optional[str] = Header(None),
):
    """
    Create a chat completion (OpenAI-compatible).

    Supports both streaming and non-streaming modes.
    """
    api_key = await get_api_key(authorization)

    if request.stream:
        return await stream_chat_completion(request, api_key)
    else:
        return await create_non_streaming_completion(request, api_key)
