/**
 * Authentication routes
 * POST /auth/login - Initiate OAuth flow
 * GET /auth/status - Check authentication status
 * POST /auth/logout - Clear credentials
 * GET /auth/config - Get auth configuration
 */

import { zValidator } from "@hono/zod-validator";
import { Hono } from "hono";
import { z } from "zod";
import type { Config } from "../config.js";
import { getLogger } from "../logger.js";
import { getOAuthManager } from "./oauth.js";
import { CredentialStorage } from "./storage.js";
import type { AuthStatus } from "./types.js";

const logger = getLogger();

export function createAuthRoutes(config: Config) {
	const app = new Hono();
	const storage = new CredentialStorage(config.DATA_DIR);
	const oauth = getOAuthManager();

	/**
	 * POST /auth/login
	 * Initiate GitHub Copilot OAuth device flow
	 */
	app.post(
		"/login",
		zValidator(
			"json",
			z.object({
				enterprise_url: z.string().optional(),
			}),
		),
		async (c) => {
			const { enterprise_url } = c.req.valid("json");

			const response = await oauth.login(
				{ enterpriseUrl: enterprise_url },
				{
					onProgress: (message) => {
						logger.info(`OAuth progress: ${message}`);
					},
				},
			);

			// Return the verification URL and code to the client
			return c.json(response);
		},
	);

	/**
	 * GET /auth/status
	 * Check current authentication status
	 */
	app.get("/status", async (c) => {
		const credentials = await storage.load();
		const authenticated = credentials !== null;

		const status: AuthStatus = {
			mode: config.AUTH_MODE,
			authenticated,
			enterpriseUrl: credentials?.enterpriseUrl || null,
		};

		return c.json(status);
	});

	/**
	 * POST /auth/logout
	 * Clear stored credentials
	 */
	app.post("/logout", async (c) => {
		await storage.clear();
		logger.info("User logged out");

		return c.json({
			status: "success",
			message: "Credentials cleared",
		});
	});

	/**
	 * GET /auth/config
	 * Get current authentication configuration
	 */
	app.get("/config", (c) => {
		return c.json({
			mode: config.AUTH_MODE,
		});
	});

	return app;
}
