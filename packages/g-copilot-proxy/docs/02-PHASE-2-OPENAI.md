# Phase 2: OpenAI-Compatible Endpoints

## Overview

Implement OpenAI-compatible `/v1/chat/completions` and `/v1/models` endpoints that proxy requests to GitHub Copilot via the pi-ai bridge.

> **IMPORTANT: No commits should be made during implementation.** This is a planning-only repository. All code changes should be made in the actual implementation package, not committed to git during the planning phase.

## OpenAI API Specification Reference

### Chat Completion Request Format

```json
{
  "model": "gpt-4",
  "messages": [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "Hello!"}
  ],
  "temperature": 1.0,
  "max_tokens": 100,
  "stream": false,
  "tools": [
    {
      "type": "function",
      "function": {
        "name": "get_weather",
        "description": "Get the current weather",
        "parameters": {
          "type": "object",
          "properties": {
            "location": {"type": "string"}
          },
          "required": ["location"]
        }
      }
    }
  ]
}
```

### Chat Completion Response Format (Non-Streaming)

```json
{
  "id": "chatcmpl-123",
  "object": "chat.completion",
  "created": 1677652288,
  "model": "gpt-4",
  "choices": [{
    "index": 0,
    "message": {
      "role": "assistant",
      "content": "Hello! How can I help you today?"
    },
    "finish_reason": "stop"
  }],
  "usage": {
    "prompt_tokens": 10,
    "completion_tokens": 9,
    "total_tokens": 19
  }
}
```

### Streaming Response Format (SSE)

```
data: {"id":"chatcmpl-123","object":"chat.completion.chunk","created":1677652288,"model":"gpt-4","choices":[{"index":0,"delta":{"content":"Hello"},"finish_reason":null}]}

data: {"id":"chatcmpl-123","object":"chat.completion.chunk","created":1677652288,"model":"gpt-4","choices":[{"index":0,"delta":{"content":"!"},"finish_reason":null}]}

data: {"id":"chatcmpl-123","object":"chat.completion.chunk","created":1677652288,"model":"gpt-4","choices":[{"index":0,"delta":{},"finish_reason":"stop"}]}

data: [DONE]
```

## Step 1: Create OpenAI Request/Response Models

#### `app/api/openai/models.py`
```python
"""OpenAI-compatible API models."""

from pydantic import BaseModel, Field
from typing import Optional, Union, List, Any, Literal
from enum import Enum


class ChatMessageRole(str, Enum):
    """Chat message role."""
    system = "system"
    user = "user"
    assistant = "assistant"
    tool = "tool"


class ChatMessage(BaseModel):
    """Chat message."""
    role: ChatMessageRole
    content: Optional[str] = None
    tool_calls: Optional[List["ChatMessageToolCall"]] = None
    tool_call_id: Optional[str] = None


class FunctionParameters(BaseModel):
    """Function parameters (JSON Schema)."""
    type: str = "object"
    properties: dict[str, Any] = Field(default_factory=dict)
    required: List[str] = Field(default_factory=list)


class ChatFunction(BaseModel):
    """Chat function definition."""
    name: str
    description: Optional[str] = None
    parameters: Optional[FunctionParameters] = None


class ChatTool(BaseModel):
    """Chat tool definition."""
    type: Literal["function"] = "function"
    function: ChatFunction


class ChatMessageToolCall(BaseModel):
    """Tool call in a message."""
    id: str
    type: Literal["function"] = "function"
    function: ChatFunction


class ChatCompletionRequest(BaseModel):
    """Chat completion request."""
    model: str
    messages: List[ChatMessage]
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    stream: Optional[bool] = False
    tools: Optional[List[ChatTool]] = None
    tool_choice: Optional[Union[Literal["auto", "none", "required"], dict]] = None


class UsageInfo(BaseModel):
    """Token usage information."""
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class ChatCompletionResponseChoice(BaseModel):
    """Choice in chat completion response."""
    index: int
    message: ChatMessage
    finish_reason: Optional[str] = None


class ChatCompletionResponse(BaseModel):
    """Chat completion response."""
    id: str
    object: Literal["chat.completion"] = "chat.completion"
    created: int
    model: str
    choices: List[ChatCompletionResponseChoice]
    usage: UsageInfo


class ChatCompletionStreamDelta(BaseModel):
    """Delta in streaming chat completion."""
    content: Optional[str] = None
    role: Optional[str] = None


class ChatCompletionStreamChoice(BaseModel):
    """Choice in streaming chat completion."""
    index: int
    delta: ChatCompletionStreamDelta
    finish_reason: Optional[str] = None


class ChatCompletionStreamResponse(BaseModel):
    """Streaming chat completion response chunk."""
    id: str
    object: Literal["chat.completion.chunk"] = "chat.completion.chunk"
    created: int
    model: str
    choices: List[ChatCompletionStreamChoice]


class ModelObject(BaseModel):
    """Model object."""
    id: str
    object: Literal["model"] = "model"
    created: int
    owned_by: str


class ModelsListResponse(BaseModel):
    """List of models response."""
    object: Literal["list"] = "list"
    data: List[ModelObject]
```

## Step 2: Create Request Mapper

The request mapper converts between OpenAI format and pi-ai format.

#### `app/core/mapper.py`
```python
"""Request/response mapping between OpenAI/Anthropic formats and pi-ai."""

import logging
from typing import Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class OpenAIMapper:
    """Mapper for OpenAI-compatible requests/responses."""

    @staticmethod
    def map_openai_to_piai_messages(
        messages: list[dict],
        system_prompt: Optional[str] = None,
    ) -> tuple[list[dict], Optional[str]]:
        """
        Convert OpenAI message format to pi-ai format.

        OpenAI format:
        [
            {"role": "system", "content": "..."},
            {"role": "user", "content": "..."},
            {"role": "assistant", "content": "...", "tool_calls": [...]}
        ]

        pi-ai format:
        [
            {"role": "user", "content": "...", "timestamp": 1234567890},
            {"role": "assistant", "content": [...], "timestamp": 1234567890}
        ]
        """
        piai_messages = []
        extracted_system = system_prompt

        for msg in messages:
            role = msg.get("role")
            content = msg.get("content")
            tool_calls = msg.get("tool_calls")
            tool_call_id = msg.get("tool_call_id")

            if role == "system":
                # pi-ai uses systemPrompt separately
                if not extracted_system:
                    extracted_system = content
                continue

            if role == "user":
                piai_msg = {
                    "role": "user",
                    "content": content or "",
                    "timestamp": int(datetime.now().timestamp() * 1000),
                }
                piai_messages.append(piai_msg)

            elif role == "assistant":
                # Build content blocks for pi-ai
                content_blocks = []

                # Add text content
                if content:
                    content_blocks.append({"type": "text", "text": content})

                # Add tool calls
                if tool_calls:
                    for tc in tool_calls:
                        fn = tc.get("function", {})
                        content_blocks.append({
                            "type": "toolCall",
                            "id": tc.get("id", ""),
                            "name": fn.get("name", ""),
                            "arguments": fn.get("parameters", {}),
                        })

                piai_msg = {
                    "role": "assistant",
                    "content": content_blocks if content_blocks else [{"type": "text", "text": ""}],
                    "timestamp": int(datetime.now().timestamp() * 1000),
                }
                piai_messages.append(piai_msg)

            elif role == "tool":
                # Tool result message
                piai_msg = {
                    "role": "toolResult",
                    "toolCallId": tool_call_id or "",
                    "toolName": "",  # Will be inferred from toolCallId
                    "content": [{"type": "text", "text": content or ""}],
                    "isError": False,
                    "timestamp": int(datetime.now().timestamp() * 1000),
                }
                piai_messages.append(piai_msg)

        return piai_messages, extracted_system

    @staticmethod
    def map_openai_tools_to_piai(tools: list[dict]) -> list[dict]:
        """
        Convert OpenAI tools format to pi-ai format.

        OpenAI: {"type": "function", "function": {...}}
        pi-ai: {"name": "...", "description": "...", "parameters": ...}
        """
        if not tools:
            return []

        piai_tools = []
        for tool in tools:
            if tool.get("type") == "function":
                fn = tool.get("function", {})
                piai_tools.append({
                    "name": fn.get("name", ""),
                    "description": fn.get("description", ""),
                    "parameters": fn.get("parameters", {}),
                })
        return piai_tools

    @staticmethod
    def map_piai_event_to_openai_chunk(
        event: dict,
        request_id: str,
        model: str,
        created: int,
    ) -> Optional[dict]:
        """
        Convert pi-ai streaming event to OpenAI chunk format.

        Returns None for events that don't map to OpenAI chunks.
        """
        event_type = event.get("type")

        if event_type == "text_delta":
            return {
                "id": request_id,
                "object": "chat.completion.chunk",
                "created": created,
                "model": model,
                "choices": [{
                    "index": 0,
                    "delta": {"content": event.get("delta", "")},
                    "finish_reason": None,
                }],
            }

        if event_type == "toolcall_start":
            # Start of a tool call - emit the tool call start
            tc = event.get("toolCall", {})
            return {
                "id": request_id,
                "object": "chat.completion.chunk",
                "created": created,
                "model": model,
                "choices": [{
                    "index": 0,
                    "delta": {
                        "tool_calls": [{
                            "index": event.get("contentIndex", 0),
                            "id": tc.get("id", ""),
                            "type": "function",
                            "function": {
                                "name": tc.get("name", ""),
                                "arguments": "",
                            },
                        }]
                    },
                    "finish_reason": None,
                }],
            }

        if event_type == "toolcall_delta":
            # Tool call argument delta
            idx = event.get("contentIndex", 0)
            delta = event.get("delta", "")
            return {
                "id": request_id,
                "object": "chat.completion.chunk",
                "created": created,
                "model": model,
                "choices": [{
                    "index": 0,
                    "delta": {
                        "tool_calls": [{
                            "index": idx,
                            "function": {
                                "arguments": delta,
                            },
                        }]
                    },
                    "finish_reason": None,
                }],
            }

        if event_type == "done":
            reason = event.get("reason", "stop")
            # Map pi-ai stop reasons to OpenAI
            finish_reason = {
                "stop": "stop",
                "length": "length",
                "toolUse": "tool_calls",
                "error": "stop",
                "aborted": "stop",
            }.get(reason, "stop")

            return {
                "id": request_id,
                "object": "chat.completion.chunk",
                "created": created,
                "model": model,
                "choices": [{
                    "index": 0,
                    "delta": {},
                    "finish_reason": finish_reason,
                }],
            }

        return None

    @staticmethod
    def map_piai_message_to_openai(
        message: dict,
        request_id: str,
        model: str,
        created: int,
    ) -> dict:
        """
        Convert completed pi-ai message to OpenAI response format.
        """
        content_blocks = message.get("content", [])
        text_parts = []
        tool_calls = []

        for block in content_blocks:
            block_type = block.get("type")

            if block_type == "text":
                text_parts.append(block.get("text", ""))

            elif block_type == "toolCall":
                tool_calls.append({
                    "id": block.get("id", ""),
                    "type": "function",
                    "function": {
                        "name": block.get("name", ""),
                        "arguments": block.get("arguments", {}),
                    },
                })

        usage = message.get("usage", {})
        finish_reason = message.get("stopReason", "stop")

        # Map pi-ai stop reasons to OpenAI
        mapped_finish_reason = {
            "stop": "stop",
            "length": "length",
            "toolUse": "tool_calls",
            "error": "stop",
            "aborted": "stop",
        }.get(finish_reason, "stop")

        return {
            "id": request_id,
            "object": "chat.completion",
            "created": created,
            "model": model,
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "".join(text_parts) if text_parts else None,
                    "tool_calls": tool_calls if tool_calls else None,
                },
                "finish_reason": mapped_finish_reason,
            }],
            "usage": {
                "prompt_tokens": usage.get("input", 0),
                "completion_tokens": usage.get("output", 0),
                "total_tokens": usage.get("totalTokens", 0),
            },
        }

    @staticmethod
    def map_piai_model_to_openai(model: dict) -> dict:
        """Convert pi-ai model to OpenAI model format."""
        return {
            "id": model.get("id", ""),
            "object": "model",
            "created": 1677610600,  # Static timestamp for compatibility
            "owned_by": "github-copilot",
        }


class AnthropicMapper:
    """Mapper for Anthropic-compatible requests/responses."""

    @staticmethod
    def map_anthropic_to_piai_messages(
        messages: list[dict],
        system_prompt: Optional[str] = None,
    ) -> tuple[list[dict], Optional[str]]:
        """
        Convert Anthropic message format to pi-ai format.

        Anthropic format:
        [
            {"role": "user", "content": "..."},
            {"role": "assistant", "content": "..."}
        ]

        Note: Anthropic uses a separate "system" parameter instead of system messages.
        """
        piai_messages = []

        for msg in messages:
            role = msg.get("role")
            content = msg.get("content")

            if role == "user":
                # Handle content as string or array of blocks
                if isinstance(content, str):
                    piai_msg = {
                        "role": "user",
                        "content": content,
                        "timestamp": int(datetime.now().timestamp() * 1000),
                    }
                else:
                    # Content is array of blocks - convert to pi-ai format
                    piai_content = []
                    for block in content:
                        block_type = block.get("type")
                        if block_type == "text":
                            piai_content.append({
                                "type": "text",
                                "text": block.get("text", ""),
                            })
                        elif block_type == "image":
                            # Anthropic images have different format
                            source = block.get("source", {})
                            piai_content.append({
                                "type": "image",
                                "data": source.get("data", ""),
                                "mimeType": source.get("media_type", "image/png"),
                            })

                    piai_msg = {
                        "role": "user",
                        "content": piai_content if piai_content else "",
                        "timestamp": int(datetime.now().timestamp() * 1000),
                    }

                piai_messages.append(piai_msg)

            elif role == "assistant":
                content_blocks = []

                if isinstance(content, str):
                    content_blocks.append({"type": "text", "text": content})
                elif isinstance(content, list):
                    for block in content:
                        block_type = block.get("type")
                        if block_type == "text":
                            content_blocks.append({
                                "type": "text",
                                "text": block.get("text", ""),
                            })
                        elif block_type == "tool_use":
                            content_blocks.append({
                                "type": "toolCall",
                                "id": block.get("id", ""),
                                "name": block.get("name", ""),
                                "arguments": block.get("input", {}),
                            })

                piai_msg = {
                    "role": "assistant",
                    "content": content_blocks if content_blocks else [{"type": "text", "text": ""}],
                    "timestamp": int(datetime.now().timestamp() * 1000),
                }
                piai_messages.append(piai_msg)

            elif role == "user" and isinstance(content, list):
                # Handle tool result blocks in Anthropic format
                has_tool_results = any(b.get("type") == "tool_result" for b in content)
                if has_tool_results:
                    for block in content:
                        if block.get("type") == "tool_result":
                            piai_msg = {
                                "role": "toolResult",
                                "toolCallId": block.get("tool_use_id", ""),
                                "toolName": "",
                                "content": [
                                    {
                                        "type": "text",
                                        "text": block.get("content", ""),
                                    }
                                ],
                                "isError": block.get("is_error", False),
                                "timestamp": int(datetime.now().timestamp() * 1000),
                            }
                            piai_messages.append(piai_msg)

        return piai_messages, system_prompt

    @staticmethod
    def map_anthropic_tools_to_piai(tools: dict) -> list[dict]:
        """
        Convert Anthropic tools format to pi-ai format.

        Anthropic: [{"name": "...", "description": "...", "input_schema": {...}}]
        pi-ai: [{"name": "...", "description": "...", "parameters": ...}]
        """
        if not tools:
            return []

        piai_tools = []
        for tool in tools:
            piai_tools.append({
                "name": tool.get("name", ""),
                "description": tool.get("description", ""),
                "parameters": tool.get("input_schema", {}),
            })
        return piai_tools

    @staticmethod
    def map_piai_event_to_anthropic_chunk(
        event: dict,
        request_id: str,
        model: str,
    ) -> Optional[dict]:
        """
        Convert pi-ai streaming event to Anthropic chunk format.

        Anthropic uses a different SSE format with event types.
        """
        event_type = event.get("type")

        if event_type == "text_start":
            return {
                "type": "content_block_start",
                "index": 0,
                "content_block": {"type": "text", "text": ""},
            }

        if event_type == "text_delta":
            return {
                "type": "content_block_delta",
                "index": 0,
                "delta": {"type": "text_delta", "text": event.get("delta", "")},
            }

        if event_type == "text_end":
            return {
                "type": "content_block_stop",
                "index": 0,
            }

        if event_type == "toolcall_start":
            tc = event.get("toolCall", {})
            idx = event.get("contentIndex", 0)
            return {
                "type": "content_block_start",
                "index": idx,
                "content_block": {
                    "type": "tool_use",
                    "id": tc.get("id", ""),
                    "name": tc.get("name", ""),
                    "input": {},
                },
            }

        if event_type == "toolcall_delta":
            idx = event.get("contentIndex", 0)
            delta = event.get("delta", "")
            # For Anthropic, we need to accumulate the full arguments
            # This is handled in the streaming response
            return None

        if event_type == "toolcall_end":
            idx = event.get("contentIndex", 0)
            return {
                "type": "content_block_stop",
                "index": idx,
            }

        if event_type == "done":
            message = event.get("message", {})
            usage = message.get("usage", {})
            return {
                "type": "message_stop",
                "message_id": request_id,
                "usage": {
                    "input_tokens": usage.get("input", 0),
                    "output_tokens": usage.get("output", 0),
                },
            }

        return None

    @staticmethod
    def map_piai_message_to_anthropic(
        message: dict,
        request_id: str,
        model: str,
    ) -> dict:
        """
        Convert completed pi-ai message to Anthropic response format.
        """
        content_blocks = message.get("content", [])
        anthropic_content = []
        stop_reason = message.get("stopReason", "stop")

        for block in content_blocks:
            block_type = block.get("type")

            if block_type == "text":
                anthropic_content.append({
                    "type": "text",
                    "text": block.get("text", ""),
                })

            elif block_type == "toolCall":
                anthropic_content.append({
                    "type": "tool_use",
                    "id": block.get("id", ""),
                    "name": block.get("name", ""),
                    "input": block.get("arguments", {}),
                })

        usage = message.get("usage", {})

        # Map pi-ai stop reasons to Anthropic
        mapped_stop_reason = {
            "stop": "end_turn",
            "length": "max_tokens",
            "toolUse": "tool_use",
            "error": "end_turn",
            "aborted": "end_turn",
        }.get(stop_reason, "end_turn")

        return {
            "id": request_id,
            "type": "message",
            "role": "assistant",
            "content": anthropic_content,
            "model": model,
            "stop_reason": mapped_stop_reason,
            "stop_sequence": None,
            "usage": {
                "input_tokens": usage.get("input", 0),
                "output_tokens": usage.get("output", 0),
            },
        }

    @staticmethod
    def map_piai_model_to_anthropic(model: dict) -> dict:
        """Convert pi-ai model to Anthropic model format."""
        return {
            "id": model.get("id", ""),
            "name": model.get("name", ""),
            "display_name": model.get("name", ""),
            "type": "model",
        }
```

#### `app/core/__init__.py` (update)
```python
"""Core utilities for g-copilot-proxy."""

from app.core.piai_bridge import PiAIBridge, PiAIBridgeError, get_piai_bridge
from app.core.mapper import OpenAIMapper, AnthropicMapper

__all__ = [
    "PiAIBridge",
    "PiAIBridgeError",
    "get_piai_bridge",
    "OpenAIMapper",
    "AnthropicMapper",
]
```

## Step 3: Implement OpenAI Chat Completions Endpoint

#### `app/api/openai/chat.py`
```python
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
    ChatCompletionStreamResponse,
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
```

## Step 4: Implement OpenAI Models Endpoint

#### `app/api/openai/models.py`
```python
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
```

## Verification

Test the OpenAI-compatible endpoints:

```bash
# Start the server
poetry run uvicorn app.main:app --reload

# Test models endpoint
curl http://localhost:8000/v1/models

# Test chat completion (non-streaming)
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_COPILOT_TOKEN" \
  -d '{
    "model": "claude-sonnet-4.5",
    "messages": [{"role": "user", "content": "Hello!"}]
  }'

# Test chat completion (streaming)
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_COPILOT_TOKEN" \
  -d '{
    "model": "claude-sonnet-4.5",
    "messages": [{"role": "user", "content": "Hello!"}],
    "stream": true
  }'
```

## Next Steps

Proceed to [Phase 3: Anthropic Endpoints](./03-PHASE-3-ANTHROPIC.md) to implement the Anthropic-compatible API.
