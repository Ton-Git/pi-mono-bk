/**
 * g-copilot-proxy entry point
 * OpenAI & Anthropic compatible proxy server for GitHub Copilot
 */

import { getConfig } from "./config.js";
import { getLogger } from "./logger.js";
import { createServer } from "./server.js";

const config = getConfig();
const logger = getLogger();

const app = createServer();

// Use Node.js adapter (not Bun)
import { serve } from "@hono/node-server";

logger.info(`Server running on http://${config.HOST}:${config.PORT}`);

const server = serve({
	fetch: app.fetch,
	port: config.PORT,
	hostname: config.HOST,
});

// Graceful shutdown
process.on("SIGTERM", () => {
	logger.info("SIGTERM received, shutting down gracefully");
	server.close?.();
	process.exit(0);
});

process.on("SIGINT", () => {
	logger.info("SIGINT received, shutting down gracefully");
	server.close?.();
	process.exit(0);
});

export default app;
