/**
 * Main server setup
 * Creates and configures the Hono application
 */

import { Hono } from "hono";
import { cors } from "hono/cors";
import { logger } from "hono/logger";
import { createAnthropicRoutes } from "./api/anthropic/routes.js";
import { createHealthRoutes } from "./api/health.js";
import { createOpenAIRoutes } from "./api/openai/routes.js";
import { createAuthMiddleware } from "./auth/middleware.js";
import { createAuthRoutes } from "./auth/routes.js";
import { getConfig } from "./config.js";
import { initLogger } from "./logger.js";

/**
 * Create and configure the Hono application
 */
export function createServer() {
	const config = getConfig();
	const app = new Hono();

	// Initialize logger
	initLogger(config);

	// CORS middleware
	const corsOrigin = config.CORS_ORIGINS.length === 1 && config.CORS_ORIGINS[0] === "*" ? "*" : config.CORS_ORIGINS;

	app.use(
		"*",
		cors({
			origin: corsOrigin,
			allowMethods: ["GET", "POST", "OPTIONS"],
			allowHeaders: ["Content-Type", "Authorization"],
		}),
	);

	// Request logging
	app.use("*", logger());

	// Health check routes (no auth required)
	const healthRoutes = createHealthRoutes(config);
	app.route("/", healthRoutes);

	// Authentication routes (no auth required)
	const authRoutes = createAuthRoutes(config);
	app.route("/auth", authRoutes);

	// Create auth middleware for protected routes
	const authMiddleware = createAuthMiddleware(config);

	// OpenAI-compatible routes (auth required)
	const openaiRoutes = createOpenAIRoutes(config);
	app.use("/v1/*", authMiddleware);
	app.route("/v1", openaiRoutes);

	// Anthropic-compatible routes share the same /v1 prefix
	const anthropicRoutes = createAnthropicRoutes(config);
	app.route("/v1", anthropicRoutes);

	// Error handling
	app.onError((err, c) => {
		console.error("Server error:", err);
		return c.json(
			{
				error: {
					message: err.message || "Internal server error",
					type: "api_error",
				},
			},
			500,
		);
	});

	// 404 handler
	app.notFound((c) => {
		return c.json(
			{
				error: {
					message: "Not found",
					type: "not_found_error",
				},
			},
			404,
		);
	});

	return app;
}
