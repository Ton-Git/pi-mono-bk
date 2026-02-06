"""GitHub Copilot OAuth handler for managed authentication mode."""

import asyncio
import json
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class GitHubCopilotOAuth:
    """Handler for GitHub Copilot OAuth flow."""

    def __init__(self, module_path: str = "../ai", node_path: str = "node"):
        self.module_path = Path(module_path).resolve()
        self.node_path = node_path

        # OAuth script template
        self.oauth_script = """
        const { loginGitHubCopilot } = require('@mariozechner/pi-ai');

        async function main() {
            try {
                const input = JSON.parse(require('fs').readFileSync(0, 'utf-8'));

                // For OAuth flow, we'll use the CLI's login mechanism
                const { login } = require('@mariozechner/pi-ai/cli');

                const credentials = await login('github-copilot', {
                    onAuth: (url, instructions) => {
                        console.log(JSON.stringify({
                            type: 'auth',
                            url: url,
                            instructions: instructions
                        }));
                    },
                    onPrompt: async (prompt) => {
                        // For automation, read from stdin
                        console.log(JSON.stringify({
                            type: 'prompt',
                            message: prompt.message
                        }));
                        return input.enterpriseUrl || '';
                    },
                    onProgress: (msg) => {
                        console.log(JSON.stringify({
                            type: 'progress',
                            message: msg
                        }));
                    }
                });

                console.log(JSON.stringify({
                    type: 'done',
                    credentials: credentials
                }));
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

    async def login(
        self,
        enterprise_url: Optional[str] = None,
        on_auth=None,
        on_progress=None,
    ) -> dict:
        """
        Perform GitHub Copilot OAuth login.

        Args:
            enterprise_url: Optional GitHub Enterprise URL
            on_auth: Callback when auth URL is available
            on_progress: Callback for progress updates

        Returns:
            OAuth credentials dict with 'access', 'refresh', 'expires' keys
        """
        payload = {"enterpriseUrl": enterprise_url}

        cmd = [
            self.node_path,
            "--eval",
            self.oauth_script,
        ]

        logger.info("Starting GitHub Copilot OAuth flow...")

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(self.module_path) if self.module_path.exists() else None,
            )

            # Send payload to stdin
            input_data = json.dumps(payload).encode("utf-8")
            process.stdin.write(input_data)
            await process.stdin.drain()
            process.stdin.close()

            credentials = None

            # Read and parse output line by line
            while True:
                line = await process.stdout.readline()
                if not line:
                    break

                line_str = line.decode("utf-8").strip()
                if not line_str:
                    continue

                try:
                    output = json.loads(line_str)
                    output_type = output.get("type")

                    if output_type == "auth":
                        url = output.get("url", "")
                        instructions = output.get("instructions")
                        if on_auth:
                            on_auth(url, instructions)
                        logger.info(f"Auth URL: {url}")
                        if instructions:
                            logger.info(f"Instructions: {instructions}")

                    elif output_type == "progress":
                        msg = output.get("message", "")
                        if on_progress:
                            on_progress(msg)
                        logger.info(f"Progress: {msg}")

                    elif output_type == "done":
                        credentials = output.get("credentials")
                        logger.info("OAuth login successful")
                        break

                    elif output_type == "error":
                        error_msg = output.get("error", "Unknown error")
                        logger.error(f"OAuth error: {error_msg}")
                        raise Exception(f"OAuth failed: {error_msg}")

                except json.JSONDecodeError:
                    logger.warning(f"Failed to parse OAuth output: {line_str}")
                    continue

            # Wait for process to complete
            returncode = await process.wait()

            if returncode != 0:
                stderr = await process.stderr.read()
                error_output = stderr.decode("utf-8")
                logger.error(f"OAuth subprocess failed: {error_output}")
                raise Exception(f"OAuth failed with return code {returncode}")

            if not credentials:
                raise Exception("OAuth completed but no credentials received")

            return credentials

        except asyncio.CancelledError:
            if process:
                process.kill()
                await process.wait()
            raise
        except Exception as e:
            logger.exception(f"OAuth login failed: {e}")
            raise


oauth_handler = GitHubCopilotOAuth()


def get_oauth_handler() -> GitHubCopilotOAuth:
    """Get OAuth handler singleton."""
    return oauth_handler
