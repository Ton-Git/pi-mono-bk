"""Anthropic-compatible messages endpoint."""

import logging
import json
import uuid
from typing import Optional
from fastapi import APIRouter, Request, HTTPException, Header
from fastapi.responses import StreamingResponse

from app.api.anthropic.models import (
    MessageRequest,
    MessageResponse,
)
from app.core import PiAIBridgeError, get_piai_bridge, AnthropicMapper

logger = logging.getLogger(__name__)
router = APIRouter()

# Default model if none specified
DEFAULT_MODEL = "claude-sonnet-4.5"

# Model alias mapping (Anthropic names -> GitHub Copilot names)
MODEL_ALIASES = {
    # Claude 3 aliases
    "claude-3-haiku-20240307": "claude-haiku-4.5",
    "claude-3-sonnet-20240229": "claude-sonnet-4",
    "claude-3-opus-20240229": "claude-opus-4.5",
    "claude-3-5-sonnet-20241022": "claude-sonnet-4.5",

    # Short aliases
    "claude-3-haiku": "claude-haiku-4.5",
    "claude-3-sonnet": "claude-sonnet-4",
    "claude-3-opus": "claude-opus-4.5",
    "claude-3.5-sonnet": "claude-sonnet-4.5",
    "claude-sonnet-4.5": "claude-sonnet-4.5",

    # Generic aliases
    "claude": "claude-sonnet-4.5",
    "default": DEFAULT_MODEL,
}


async def get_api_key(authorization: Optional[str] = None) -> Optional[str]:
    """Extract API key from Authorization header.

    Anthropic uses: Authorization: Bearer sk-ant-...
    Also supports: x-api-key header
    """
    if authorization:
        if authorization.startswith("Bearer "):
            return authorization[7:]
        return authorization
    return None


def resolve_model(model: str) -> str:
    """Resolve model alias to actual GitHub Copilot model ID."""
    return MODEL_ALIASES.get(model, model)


async def stream_message(
    request: MessageRequest,
    api_key: Optional[str],
):
    """Stream message from pi-ai in Anthropic SSE format."""
    bridge = get_piai_bridge()
    request_id = f"msg_{uuid.uuid4().hex[:24]}"
    model = resolve_model(request.model)

    # Convert Anthropic format to pi-ai format
    anthropic_messages = [msg.model_dump() for msg in request.messages]
    piai_messages, system_prompt = AnthropicMapper.map_anthropic_to_piai_messages(
        anthropic_messages,
        request.system,
    )

    piai_tools = None
    if request.tools:
        anthropic_tools = [t.model_dump() for t in request.tools]
        piai_tools = AnthropicMapper.map_anthropic_tools_to_piai(anthropic_tools)

    logger.info(f"Streaming message: model={model}, messages={len(piai_messages)}")

    # Track accumulated tool call arguments
    tool_call_args: dict[int, str] = {}

    async def event_generator():
        """Generate SSE events in Anthropic format."""
        # Send message_start event
        yield {
            "event": "message_start",
            "data": {
                "type": "message_start",
                "message": {
                    "id": request_id,
                    "type": "message",
                    "role": "assistant",
                    "content": [],
                    "model": model,
                    "stop_reason": None,
                },
            },
        }

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
                event_type = event.get("type")

                # Handle text content
                if event_type == "text_start":
                    yield {
                        "event": "content_block_start",
                        "data": {
                            "type": "content_block_start",
                            "index": 0,
                            "content_block": {"type": "text", "text": ""},
                        },
                    }

                elif event_type == "text_delta":
                    yield {
                        "event": "content_block_delta",
                        "data": {
                            "type": "content_block_delta",
                            "index": 0,
                            "delta": {"type": "text_delta", "text": event.get("delta", "")},
                        },
                    }

                elif event_type == "text_end":
                    yield {
                        "event": "content_block_stop",
                        "data": {"type": "content_block_stop", "index": 0},
                    }

                # Handle tool calls
                elif event_type == "toolcall_start":
                    idx = event.get("contentIndex", 0)
                    tc = event.get("toolCall", {})
                    tool_call_args[idx] = ""

                    yield {
                        "event": "content_block_start",
                        "data": {
                            "type": "content_block_start",
                            "index": idx,
                            "content_block": {
                                "type": "tool_use",
                                "id": tc.get("id", ""),
                                "name": tc.get("name", ""),
                                "input": {},
                            },
                        },
                    }

                elif event_type == "toolcall_delta":
                    idx = event.get("contentIndex", 0)
                    delta = event.get("delta", "")
                    tool_call_args[idx] = (tool_call_args.get(idx, "") + delta)

                    # Anthropic sends partial input as delta
                    try:
                        partial_args = json.loads(tool_call_args[idx])
                        yield {
                            "event": "content_block_delta",
                            "data": {
                                "type": "content_block_delta",
                                "index": idx,
                                "delta": {"type": "input_json_delta", "partial_json": delta},
                            },
                        }
                    except json.JSONDecodeError:
                        # Not valid JSON yet, just send the raw delta
                        yield {
                            "event": "content_block_delta",
                            "data": {
                                "type": "content_block_delta",
                                "index": idx,
                                "delta": {"type": "input_json_delta", "partial_json": delta},
                            },
                        }

                elif event_type == "toolcall_end":
                    idx = event.get("contentIndex", 0)
                    yield {
                        "event": "content_block_stop",
                        "data": {"type": "content_block_stop", "index": idx},
                    }

                # Handle completion
                elif event_type == "done":
                    message = event.get("message", {})
                    usage = message.get("usage", {})
                    stop_reason = message.get("stopReason", "stop")

                    # Map pi-ai stop reasons to Anthropic
                    mapped_stop_reason = {
                        "stop": "end_turn",
                        "length": "max_tokens",
                        "toolUse": "tool_use",
                        "error": "end_turn",
                        "aborted": "end_turn",
                    }.get(stop_reason, "end_turn")

                    yield {
                        "event": "message_delta",
                        "data": {
                            "type": "message_delta",
                            "delta": {"stop_reason": mapped_stop_reason, "stop_sequence": None},
                            "usage": {
                                "output_tokens": usage.get("output", 0),
                            },
                        },
                    }

                    yield {
                        "event": "message_stop",
                        "data": {"type": "message_stop"},
                    }

        except PiAIBridgeError as e:
            logger.error(f"pi-ai bridge error: {e.message}")
            yield {
                "event": "error",
                "data": {"type": "error", "error": {"message": e.message}},
            }

        except Exception as e:
            logger.exception(f"Unexpected error in stream: {e}")
            yield {
                "event": "error",
                "data": {"type": "error", "error": {"message": str(e)}},
            }

    return StreamingResponse(
        anthropic_sse_generator(event_generator()),
        media_type="text/event-stream",
    )


async def anthropic_sse_generator(event_generator):
    """Convert event dict generator to Anthropic SSE format."""
    async for event_dict in event_generator():
        event_type = event_dict.get("event", "")
        data = event_dict.get("data", {})

        yield f"event: {event_type}\n"
        yield f"data: {json.dumps(data)}\n\n"


async def create_non_streaming_message(
    request: MessageRequest,
    api_key: Optional[str],
) -> MessageResponse:
    """Create non-streaming message."""
    bridge = get_piai_bridge()
    request_id = f"msg_{uuid.uuid4().hex[:24]}"
    model = resolve_model(request.model)

    # Convert Anthropic format to pi-ai format
    anthropic_messages = [msg.model_dump() for msg in request.messages]
    piai_messages, system_prompt = AnthropicMapper.map_anthropic_to_piai_messages(
        anthropic_messages,
        request.system,
    )

    piai_tools = None
    if request.tools:
        anthropic_tools = [t.model_dump() for t in request.tools]
        piai_tools = AnthropicMapper.map_anthropic_tools_to_piai(anthropic_tools)

    logger.info(f"Creating message: model={model}, messages={len(piai_messages)}")

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
                detail="Failed to get message from pi-ai",
            )

        response_data = AnthropicMapper.map_piai_message_to_anthropic(
            final_message,
            request_id,
            model,
        )

        return MessageResponse(**response_data)

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


@router.post("/messages", response_model=None)
async def create_message(
    request: MessageRequest,
    authorization: Optional[str] = Header(None),
    x_api_key: Optional[str] = Header(None, alias="x-api-key"),
):
    """
    Create a message (Anthropic-compatible).

    Supports both streaming and non-streaming modes.

    The API key can be provided via:
    - Authorization header: Bearer sk-ant-...
    - x-api-key header
    """
    # Anthropic supports both Authorization and x-api-key headers
    api_key = await get_api_key(authorization) or x_api_key

    if request.stream:
        return await stream_message(request, api_key)
    else:
        return await create_non_streaming_message(request, api_key)
