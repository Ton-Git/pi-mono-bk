"""Tests for request/response mappers."""

import pytest
from datetime import datetime

from app.core.mapper import OpenAIMapper, AnthropicMapper


class TestOpenAIMapper:
    """Test OpenAIMapper class."""

    def test_map_openai_to_piai_simple_user_message(self):
        """Test mapping simple user message."""
        messages = [{"role": "user", "content": "Hello!"}]
        piai_msgs, system = OpenAIMapper.map_openai_to_piai_messages(messages)

        assert len(piai_msgs) == 1
        assert piai_msgs[0]["role"] == "user"
        assert piai_msgs[0]["content"] == "Hello!"
        assert "timestamp" in piai_msgs[0]
        assert system is None

    def test_map_openai_to_piai_with_system_message(self):
        """Test mapping with system message extracts system prompt."""
        messages = [
            {"role": "system", "content": "You are helpful."},
            {"role": "user", "content": "Hello!"}
        ]
        piai_msgs, system = OpenAIMapper.map_openai_to_piai_messages(messages)

        assert len(piai_msgs) == 1  # System message is extracted, not in messages
        assert system == "You are helpful."
        assert piai_msgs[0]["role"] == "user"

    def test_map_openai_to_piai_with_assistant_message(self):
        """Test mapping assistant message."""
        messages = [
            {"role": "user", "content": "Hello!"},
            {"role": "assistant", "content": "Hi there!"}
        ]
        piai_msgs, system = OpenAIMapper.map_openai_to_piai_messages(messages)

        assert len(piai_msgs) == 2
        assert piai_msgs[1]["role"] == "assistant"
        assert piai_msgs[1]["content"] == [{"type": "text", "text": "Hi there!"}]

    def test_map_openai_to_piai_with_tool_calls(self):
        """Test mapping assistant message with tool calls."""
        messages = [
            {"role": "user", "content": "What's the weather?"},
            {"role": "assistant", "content": None, "tool_calls": [
                {
                    "id": "call_123",
                    "type": "function",
                    "function": {
                        "name": "get_weather",
                        "parameters": {"location": "NYC"}
                    }
                }
            ]}
        ]
        piai_msgs, system = OpenAIMapper.map_openai_to_piai_messages(messages)

        assert len(piai_msgs) == 2
        assert piai_msgs[1]["role"] == "assistant"
        assert len(piai_msgs[1]["content"]) == 1
        assert piai_msgs[1]["content"][0]["type"] == "toolCall"
        assert piai_msgs[1]["content"][0]["id"] == "call_123"
        assert piai_msgs[1]["content"][0]["name"] == "get_weather"

    def test_map_openai_to_piai_with_tool_result(self):
        """Test mapping tool result message."""
        messages = [
            {"role": "tool", "tool_call_id": "call_123", "content": "72 degrees"}
        ]
        piai_msgs, system = OpenAIMapper.map_openai_to_piai_messages(messages)

        assert len(piai_msgs) == 1
        assert piai_msgs[0]["role"] == "toolResult"
        assert piai_msgs[0]["toolCallId"] == "call_123"

    def test_map_openai_to_piai_custom_system_param(self):
        """Test mapping with custom system parameter."""
        messages = [{"role": "user", "content": "Hello!"}]
        piai_msgs, system = OpenAIMapper.map_openai_to_piai_messages(
            messages,
            system_prompt="Custom system prompt"
        )

        assert system == "Custom system prompt"

    def test_map_openai_tools_to_piai(self):
        """Test mapping OpenAI tools to pi-ai format."""
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "get_weather",
                    "description": "Get weather info",
                    "parameters": {"type": "object", "properties": {}}
                }
            }
        ]
        piai_tools = OpenAIMapper.map_openai_tools_to_piai(tools)

        assert len(piai_tools) == 1
        assert piai_tools[0]["name"] == "get_weather"
        assert piai_tools[0]["description"] == "Get weather info"

    def test_map_openai_tools_to_piai_empty(self):
        """Test mapping empty tools list."""
        piai_tools = OpenAIMapper.map_openai_tools_to_piai([])
        assert piai_tools == []

    def test_map_openai_tools_to_piai_none(self):
        """Test mapping None tools."""
        piai_tools = OpenAIMapper.map_openai_tools_to_piai(None)
        assert piai_tools == []

    def test_map_piai_event_to_openai_chunk_text_delta(self):
        """Test mapping text delta event to OpenAI chunk."""
        event = {"type": "text_delta", "delta": "Hello"}
        chunk = OpenAIMapper.map_piai_event_to_openai_chunk(
            event, "req-123", "claude-sonnet-4.5", 1234567890
        )

        assert chunk is not None
        assert chunk["object"] == "chat.completion.chunk"
        assert chunk["choices"][0]["delta"]["content"] == "Hello"

    def test_map_piai_event_to_openai_chunk_toolcall_start(self):
        """Test mapping tool call start event to OpenAI chunk."""
        event = {
            "type": "toolcall_start",
            "toolCall": {"id": "call_123", "name": "get_weather"},
            "contentIndex": 0
        }
        chunk = OpenAIMapper.map_piai_event_to_openai_chunk(
            event, "req-123", "claude-sonnet-4.5", 1234567890
        )

        assert chunk is not None
        assert chunk["choices"][0]["delta"]["tool_calls"][0]["id"] == "call_123"

    def test_map_piai_event_to_openai_chunk_done(self):
        """Test mapping done event to OpenAI chunk."""
        event = {"type": "done", "reason": "stop"}
        chunk = OpenAIMapper.map_piai_event_to_openai_chunk(
            event, "req-123", "claude-sonnet-4.5", 1234567890
        )

        assert chunk is not None
        assert chunk["choices"][0]["finish_reason"] == "stop"

    def test_map_piai_event_to_openai_chunk_unknown_event(self):
        """Test mapping unknown event returns None."""
        event = {"type": "unknown_event"}
        chunk = OpenAIMapper.map_piai_event_to_openai_chunk(
            event, "req-123", "claude-sonnet-4.5", 1234567890
        )

        assert chunk is None

    def test_map_piai_message_to_openai(self):
        """Test mapping pi-ai message to OpenAI format."""
        message = {
            "content": [
                {"type": "text", "text": "Hello!"},
                {"type": "toolCall", "id": "call_123", "name": "func", "arguments": {}}
            ],
            "stopReason": "stop",
            "usage": {"input": 10, "output": 20, "totalTokens": 30}
        }
        response = OpenAIMapper.map_piai_message_to_openai(
            message, "req-123", "claude-sonnet-4.5", 1234567890
        )

        assert response["object"] == "chat.completion"
        assert response["choices"][0]["message"]["content"] == "Hello!"
        assert response["choices"][0]["finish_reason"] == "stop"
        assert response["usage"]["prompt_tokens"] == 10
        assert response["usage"]["completion_tokens"] == 20

    def test_map_piai_model_to_openai(self):
        """Test mapping pi-ai model to OpenAI format."""
        model = {"id": "claude-sonnet-4.5", "name": "Claude Sonnet 4.5"}
        openai_model = OpenAIMapper.map_piai_model_to_openai(model)

        assert openai_model["id"] == "claude-sonnet-4.5"
        assert openai_model["object"] == "model"
        assert openai_model["owned_by"] == "github-copilot"


class TestAnthropicMapper:
    """Test AnthropicMapper class."""

    def test_map_anthropic_to_piai_user_message_string(self):
        """Test mapping user message with string content."""
        messages = [{"role": "user", "content": "Hello!"}]
        piai_msgs, system = AnthropicMapper.map_anthropic_to_piai_messages(messages)

        assert len(piai_msgs) == 1
        assert piai_msgs[0]["role"] == "user"
        assert piai_msgs[0]["content"] == "Hello!"

    def test_map_anthropic_to_piai_user_message_blocks(self):
        """Test mapping user message with content blocks."""
        messages = [{
            "role": "user",
            "content": [
                {"type": "text", "text": "Hello!"},
                {"type": "image", "source": {"media_type": "image/png", "data": "base64..."}}
            ]
        }]
        piai_msgs, system = AnthropicMapper.map_anthropic_to_piai_messages(messages)

        assert len(piai_msgs) == 1
        assert len(piai_msgs[0]["content"]) == 2
        assert piai_msgs[0]["content"][0]["type"] == "text"

    def test_map_anthropic_to_piai_assistant_message_string(self):
        """Test mapping assistant message with string content."""
        messages = [
            {"role": "user", "content": "Hello!"},
            {"role": "assistant", "content": "Hi there!"}
        ]
        piai_msgs, system = AnthropicMapper.map_anthropic_to_piai_messages(messages)

        assert len(piai_msgs) == 2
        assert piai_msgs[1]["role"] == "assistant"
        assert piai_msgs[1]["content"][0]["text"] == "Hi there!"

    def test_map_anthropic_to_piai_assistant_message_blocks(self):
        """Test mapping assistant message with content blocks."""
        messages = [{
            "role": "assistant",
            "content": [
                {"type": "text", "text": "Let me help."},
                {"type": "tool_use", "id": "tool_123", "name": "func", "input": {}}
            ]
        }]
        piai_msgs, system = AnthropicMapper.map_anthropic_to_piai_messages(messages)

        assert len(piai_msgs) == 1
        assert piai_msgs[0]["content"][0]["type"] == "text"
        assert piai_msgs[0]["content"][1]["type"] == "toolCall"

    def test_map_anthropic_tools_to_piai(self):
        """Test mapping Anthropic tools to pi-ai format."""
        tools = [
            {
                "name": "get_weather",
                "description": "Get weather",
                "input_schema": {"type": "object"}
            }
        ]
        piai_tools = AnthropicMapper.map_anthropic_tools_to_piai(tools)

        assert len(piai_tools) == 1
        assert piai_tools[0]["name"] == "get_weather"
        assert piai_tools[0]["parameters"] == {"type": "object"}

    def test_map_anthropic_tools_to_piai_empty(self):
        """Test mapping empty tools list."""
        piai_tools = AnthropicMapper.map_anthropic_tools_to_piai([])
        assert piai_tools == []

    def test_map_piai_event_to_anthropic_chunk_text_start(self):
        """Test mapping text start event to Anthropic chunk."""
        event = {"type": "text_start"}
        chunk = AnthropicMapper.map_piai_event_to_anthropic_chunk(
            event, "msg-123", "claude-sonnet-4.5"
        )

        assert chunk is not None
        assert chunk["type"] == "content_block_start"
        assert chunk["content_block"]["type"] == "text"

    def test_map_piai_event_to_anthropic_chunk_text_delta(self):
        """Test mapping text delta event to Anthropic chunk."""
        event = {"type": "text_delta", "delta": "Hello"}
        chunk = AnthropicMapper.map_piai_event_to_anthropic_chunk(
            event, "msg-123", "claude-sonnet-4.5"
        )

        assert chunk is not None
        assert chunk["type"] == "content_block_delta"
        assert chunk["delta"]["text"] == "Hello"

    def test_map_piai_event_to_anthropic_chunk_done(self):
        """Test mapping done event to Anthropic chunk."""
        event = {
            "type": "done",
            "message": {
                "usage": {"input": 10, "output": 20}
            }
        }
        chunk = AnthropicMapper.map_piai_event_to_anthropic_chunk(
            event, "msg-123", "claude-sonnet-4.5"
        )

        assert chunk is not None
        assert chunk["type"] == "message_stop"
        assert chunk["usage"]["input_tokens"] == 10

    def test_map_piai_message_to_anthropic(self):
        """Test mapping pi-ai message to Anthropic format."""
        message = {
            "content": [
                {"type": "text", "text": "Hello!"}
            ],
            "stopReason": "end_turn",
            "usage": {"input": 10, "output": 20}
        }
        response = AnthropicMapper.map_piai_message_to_anthropic(
            message, "msg-123", "claude-sonnet-4.5"
        )

        assert response["type"] == "message"
        assert response["role"] == "assistant"
        assert response["content"][0]["text"] == "Hello!"
        assert response["stop_reason"] == "end_turn"
        assert response["usage"]["input_tokens"] == 10

    def test_map_piai_model_to_anthropic(self):
        """Test mapping pi-ai model to Anthropic format."""
        model = {"id": "claude-sonnet-4.5", "name": "Claude Sonnet 4.5"}
        anthropic_model = AnthropicMapper.map_piai_model_to_anthropic(model)

        assert anthropic_model["id"] == "claude-sonnet-4.5"
        assert anthropic_model["name"] == "Claude Sonnet 4.5"
        assert anthropic_model["type"] == "model"


class TestStopReasonMapping:
    """Test stop reason mapping between formats."""

    def test_openai_stop_reason_mapping(self):
        """Test various stop reasons map to OpenAI format."""
        reasons = ["stop", "length", "toolUse", "error", "aborted"]
        for reason in reasons:
            message = {"content": [], "stopReason": reason, "usage": {}}
            response = OpenAIMapper.map_piai_message_to_openai(
                message, "req-123", "claude", 1234567890
            )
            assert response["choices"][0]["finish_reason"] in ["stop", "length", "tool_calls"]

    def test_anthropic_stop_reason_mapping(self):
        """Test various stop reasons map to Anthropic format."""
        reasons = ["stop", "length", "toolUse", "error", "aborted"]
        for reason in reasons:
            message = {"content": [], "stopReason": reason, "usage": {}}
            response = AnthropicMapper.map_piai_message_to_anthropic(
                message, "msg-123", "claude"
            )
            assert response["stop_reason"] in ["end_turn", "max_tokens", "tool_use"]
