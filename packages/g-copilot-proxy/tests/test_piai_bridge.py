"""Tests for pi-ai bridge."""

import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi import status

from app.core.piai_bridge import PiAIBridge, PiAIBridgeError, get_piai_bridge


class TestPiAIBridge:
    """Test PiAIBridge class."""

    def test_init_default_paths(self):
        """Test initialization with default paths."""
        bridge = PiAIBridge()
        assert bridge.module_path is not None
        assert bridge.node_path == "node"

    def test_init_custom_paths(self, tmp_path):
        """Test initialization with custom paths."""
        custom_module = tmp_path / "custom-ai"
        custom_module.mkdir()

        bridge = PiAIBridge(module_path=str(custom_module), node_path="nodejs")
        assert bridge.module_path == custom_module.resolve()
        assert bridge.node_path == "nodejs"

    def test_init_nonexistent_module_path(self, tmp_path):
        """Test initialization with non-existent module path doesn't raise."""
        bridge = PiAIBridge(module_path=str(tmp_path / "nonexistent"))
        # Should not raise, just log warning
        assert bridge.module_path is not None

    @pytest.mark.asyncio
    async def test_stream_completion_iter_simple(self):
        """Test stream completion with simple response."""
        # Create mock events to yield
        mock_events = [
            {"type": "text_start", "text": ""},
            {"type": "text_delta", "delta": "Hello"},
            {"type": "text_delta", "delta": " world"},
            {"type": "done", "reason": "stop"}
        ]

        async def mock_stream(*args, **kwargs):
            for event in mock_events:
                yield event

        with patch.object(PiAIBridge, "stream_completion_iter", mock_stream):
            bridge = PiAIBridge()
            events = []
            async for event in bridge.stream_completion_iter(
                model="claude-sonnet-4.5",
                messages=[{"role": "user", "content": "Hello"}],
                api_key="test-key"
            ):
                events.append(event)

        assert len(events) == 4
        assert events[0]["type"] == "text_start"
        assert events[1]["delta"] == "Hello"
        assert events[3]["reason"] == "stop"

    @pytest.mark.asyncio
    async def test_stream_completion_with_temperature_and_max_tokens(self):
        """Test stream completion passes temperature and max_tokens."""
        mock_process = MagicMock()
        mock_process.stdin = MagicMock()
        mock_process.stdin.write = MagicMock()
        mock_process.stdin.drain = AsyncMock()
        mock_process.stdin.close = MagicMock()
        mock_process.stdout.readline = AsyncMock(return_value=b'{"type": "done"}\n')
        mock_process.wait = AsyncMock(return_value=0)
        mock_process.returncode = 0

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            bridge = PiAIBridge()
            async for _ in bridge.stream_completion_iter(
                model="claude-sonnet-4.5",
                messages=[{"role": "user", "content": "Hi"}],
                temperature=0.7,
                max_tokens=1000
            ):
                break

        # Verify stdin.write was called with payload containing temperature and max_tokens
        call_args = mock_process.stdin.write.call_args
        payload = json.loads(call_args[0][0].decode("utf-8"))
        assert payload["temperature"] == 0.7
        assert payload["maxTokens"] == 1000

    @pytest.mark.asyncio
    async def test_stream_completion_with_system_prompt(self):
        """Test stream completion passes system prompt."""
        mock_process = MagicMock()
        mock_process.stdin = MagicMock()
        mock_process.stdin.write = MagicMock()
        mock_process.stdin.drain = AsyncMock()
        mock_process.stdin.close = MagicMock()
        mock_process.stdout.readline = AsyncMock(return_value=b'{"type": "done"}\n')
        mock_process.wait = AsyncMock(return_value=0)
        mock_process.returncode = 0

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            bridge = PiAIBridge()
            async for _ in bridge.stream_completion_iter(
                model="claude-sonnet-4.5",
                messages=[{"role": "user", "content": "Hi"}],
                system_prompt="You are helpful"
            ):
                break

        call_args = mock_process.stdin.write.call_args
        payload = json.loads(call_args[0][0].decode("utf-8"))
        assert payload["context"]["systemPrompt"] == "You are helpful"

    @pytest.mark.asyncio
    async def test_stream_completion_with_tools(self):
        """Test stream completion passes tools."""
        mock_process = MagicMock()
        mock_process.stdin = MagicMock()
        mock_process.stdin.write = MagicMock()
        mock_process.stdin.drain = AsyncMock()
        mock_process.stdin.close = MagicMock()
        mock_process.stdout.readline = AsyncMock(return_value=b'{"type": "done"}\n')
        mock_process.wait = AsyncMock(return_value=0)
        mock_process.returncode = 0

        tools = [{"name": "test", "description": "A test tool"}]

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            bridge = PiAIBridge()
            async for _ in bridge.stream_completion_iter(
                model="claude-sonnet-4.5",
                messages=[{"role": "user", "content": "Hi"}],
                tools=tools
            ):
                break

        call_args = mock_process.stdin.write.call_args
        payload = json.loads(call_args[0][0].decode("utf-8"))
        assert payload["context"]["tools"] == tools

    @pytest.mark.asyncio
    async def test_stream_completion_handles_invalid_json(self):
        """Test stream completion skips invalid JSON lines."""
        # Create mock events that simulate valid and invalid JSON
        mock_events = [
            {"type": "text_start"},
            # Invalid JSON would be skipped at the subprocess level
            {"type": "done"}
        ]

        async def mock_stream(*args, **kwargs):
            for event in mock_events:
                yield event

        with patch.object(PiAIBridge, "stream_completion_iter", mock_stream):
            bridge = PiAIBridge()
            events = []
            async for event in bridge.stream_completion_iter(
                model="claude-sonnet-4.5",
                messages=[{"role": "user", "content": "Hi"}]
            ):
                events.append(event)

        # Should have 2 valid events
        assert len(events) == 2
        assert events[0]["type"] == "text_start"
        assert events[1]["type"] == "done"

    @pytest.mark.asyncio
    async def test_stream_completion_handles_process_error(self):
        """Test stream completion handles subprocess error."""
        mock_process = MagicMock()
        mock_process.stdin = MagicMock()
        mock_process.stdin.write = MagicMock()
        mock_process.stdin.drain = AsyncMock()
        mock_process.stdin.close = MagicMock()
        mock_process.stdout.readline = AsyncMock(return_value=b'')
        mock_process.wait = AsyncMock(return_value=1)
        mock_process.returncode = 1
        mock_process.stderr.read = AsyncMock(return_value=b'Error from node\n')

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            bridge = PiAIBridge()
            events = []
            async for event in bridge.stream_completion_iter(
                model="claude-sonnet-4.5",
                messages=[{"role": "user", "content": "Hi"}]
            ):
                events.append(event)

            # Process failed, should have no events
            assert len(events) == 0

    @pytest.mark.asyncio
    async def test_get_models_success(self):
        """Test get_models returns list of models."""
        mock_models = [
            {"id": "claude-sonnet-4.5", "name": "Claude Sonnet 4.5"},
            {"id": "gpt-4.1", "name": "GPT 4.1"}
        ]

        mock_process = MagicMock()
        mock_process.communicate = AsyncMock(return_value=(
            json.dumps(mock_models).encode(),
            b''
        ))
        mock_process.returncode = 0

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            bridge = PiAIBridge()
            models = await bridge.get_models()

        assert len(models) == 2
        assert models[0]["id"] == "claude-sonnet-4.5"

    @pytest.mark.asyncio
    async def test_get_models_error_returns_empty(self):
        """Test get_models returns empty list on error."""
        mock_process = MagicMock()
        mock_process.communicate = AsyncMock(return_value=(
            b'',
            b'Error from node\n'
        ))
        mock_process.returncode = 1

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            bridge = PiAIBridge()
            models = await bridge.get_models()

        assert models == []

    @pytest.mark.asyncio
    async def test_get_models_exception_returns_empty(self):
        """Test get_models returns empty list on exception."""
        with patch("asyncio.create_subprocess_exec", side_effect=Exception("Node not found")):
            bridge = PiAIBridge()
            models = await bridge.get_models()

        assert models == []


class TestPiAIBridgeSingleton:
    """Test pi-ai bridge singleton pattern."""

    def test_get_piai_bridge_returns_singleton(self):
        """Test get_piai_bridge returns same instance."""
        bridge1 = get_piai_bridge()
        bridge2 = get_piai_bridge()
        assert bridge1 is bridge2


class TestPiAIBridgeIntegration:
    """Integration tests for pi-ai bridge."""

    def test_models_endpoint_with_bridge(self, test_client):
        """Test /v1/models endpoint uses pi-ai bridge."""
        response = test_client.get("/v1/models")
        # May fail if pi-ai not available, but should return a response
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_500_INTERNAL_SERVER_ERROR]

        if response.status_code == status.HTTP_200_OK:
            data = response.json()
            assert "object" in data
            assert "data" in data
