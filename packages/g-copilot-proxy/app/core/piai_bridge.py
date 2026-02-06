"""Bridge to @mariozechner/pi-ai Node.js library."""

import asyncio
import json
import logging
from pathlib import Path
from typing import Any, Optional
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Node.js script template for streaming responses
PIAI_STREAM_SCRIPT = """
const { getModel, stream } = require('@mariozechner/pi-ai');

async function main() {
    try {
        const input = JSON.parse(require('fs').readFileSync(0, 'utf-8'));
        const model = getModel('github-copilot', input.model);
        const context = input.context;

        // Add API key if provided
        const options = {};
        if (input.apiKey) options.apiKey = input.apiKey;
        if (input.temperature !== undefined) options.temperature = input.temperature;
        if (input.maxTokens !== undefined) options.maxTokens = input.maxTokens;

        const s = stream(model, context, options);

        for await (const event of s) {
            console.log(JSON.stringify(event));
        }
    } catch (error) {
        console.error(JSON.stringify({
            type: 'error',
            error: error.message || String(error)
        }));
        process.exit(1);
    }
}

main();
"""

# Node.js script for getting available models
PIAI_MODELS_SCRIPT = """
const { getModels } = require('@mariozechner/pi-ai');

try {
    const models = getModels('github-copilot');
    console.log(JSON.stringify(models));
} catch (error) {
    console.error(JSON.stringify({
        type: 'error',
        error: error.message || String(error)
    }));
    process.exit(1);
}
"""


class PiAIBridgeError(Exception):
    """Exception raised when pi-ai bridge encounters an error."""

    def __init__(self, message: str, details: Optional[dict] = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class PiAIBridge:
    """Bridge to @mariozechner/pi-ai library via Node.js subprocess."""

    def __init__(
        self,
        module_path: Optional[str] = None,
        node_path: Optional[str] = None,
    ):
        """
        Initialize the pi-ai bridge.

        Args:
            module_path: Path to the pi-ai Node.js module
            node_path: Path to Node.js executable
        """
        self.module_path = Path(module_path or settings.piai_module_path).resolve()
        self.node_path = node_path or settings.piai_node_path

        if not self.module_path.exists():
            logger.warning(f"pi-ai module not found at {self.module_path}, will use runtime path")

    async def stream_completion_iter(
        self,
        model: str,
        messages: list[dict],
        api_key: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        tools: Optional[list[dict]] = None,
        system_prompt: Optional[str] = None,
    ):
        """
        Stream completion from pi-ai, yielding events line by line.

        This is an async generator that yields events as they arrive.
        """
        payload = {
            "model": model,
            "context": {
                "messages": messages,
                "tools": tools or [],
            },
        }

        if system_prompt:
            payload["context"]["systemPrompt"] = system_prompt
        if api_key:
            payload["apiKey"] = api_key
        if temperature is not None:
            payload["temperature"] = temperature
        if max_tokens is not None:
            payload["maxTokens"] = max_tokens

        cmd = [
            self.node_path,
            "--eval",
            PIAI_STREAM_SCRIPT,
        ]

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(self.module_path) if self.module_path.exists() else None,
        )

        # Write payload and close stdin
        input_data = json.dumps(payload).encode("utf-8")
        process.stdin.write(input_data)
        await process.stdin.drain()
        process.stdin.close()

        try:
            # Read and parse output line by line
            while True:
                line = await process.stdout.readline()
                if not line:
                    break

                line_str = line.decode("utf-8").strip()
                if not line_str:
                    continue

                try:
                    event = json.loads(line_str)
                    yield event
                except json.JSONDecodeError:
                    logger.warning(f"Failed to parse pi-ai output: {line_str}")
                    continue

            # Wait for process to complete
            returncode = await process.wait()

            if returncode != 0:
                stderr = await process.stderr.read()
                error_output = stderr.decode("utf-8")
                logger.error(f"pi-ai subprocess failed: {error_output}")

        except asyncio.CancelledError:
            process.kill()
            await process.wait()
            raise
        finally:
            if process.returncode is None:
                process.kill()
                await process.wait()

    async def get_models(self) -> list[dict]:
        """
        Get available models from pi-ai.

        Returns:
            List of model dictionaries

        Raises:
            PiAIBridgeError: If the subprocess fails
        """
        cmd = [
            self.node_path,
            "--eval",
            PIAI_MODELS_SCRIPT,
        ]

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(self.module_path) if self.module_path.exists() else None,
            )

            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                error_output = stderr.decode("utf-8")
                logger.error(f"pi-ai get_models failed: {error_output}")
                # Return empty list on error instead of raising
                return []

            return json.loads(stdout.decode("utf-8"))

        except Exception as e:
            logger.error(f"Failed to execute pi-ai get_models: {e}")
            return []


# Singleton instance
_bridge_instance: Optional[PiAIBridge] = None


def get_piai_bridge() -> PiAIBridge:
    """Get or create the singleton pi-ai bridge instance."""
    global _bridge_instance
    if _bridge_instance is None:
        _bridge_instance = PiAIBridge()
    return _bridge_instance
