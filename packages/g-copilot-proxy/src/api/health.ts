/**
 * Health check and root endpoints
 */

import { Hono } from "hono";
import type { Config } from "../config.js";

export function createHealthRoutes(config: Config) {
	const app = new Hono();

	/**
	 * GET /
	 * Root endpoint with app information
	 */
	app.get("/", (c) => {
		return c.json({
			name: "g-copilot-proxy",
			version: "1.0.0",
			description: "OpenAI & Anthropic compatible proxy server for GitHub Copilot",
			auth_mode: config.AUTH_MODE,
		});
	});

	/**
	 * GET /health
	 * Health check endpoint
	 */
	app.get("/health", (c) => {
		return c.json({
			status: "ok",
			timestamp: new Date().toISOString(),
		});
	});

	return app;
}
