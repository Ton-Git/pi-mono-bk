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
    def map_anthropic_tools_to_piai(tools: list[dict]) -> list[dict]:
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
