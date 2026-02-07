/**
 * Authentication middleware
 * Validates Bearer tokens or uses managed mode credentials
 */

import type { Context, Next } from "hono";
import type { Config } from "../config.js";
import { getLogger } from "../logger.js";
import { CredentialStorage } from "./storage.js";

const logger = getLogger();

/**
 * Authentication context attached to requests
 */
export interface AuthContext {
	accessToken: string;
	enterpriseUrl?: string;
	source: "bearer" | "managed";
}

/**
 * Create authentication middleware
 */
export function createAuthMiddleware(config: Config) {
	const storage = new CredentialStorage(config.DATA_DIR);

	return async (c: Context, next: Next) => {
		// In passthrough mode, look for Bearer token
		if (config.AUTH_MODE === "passthrough") {
			const authHeader = c.req.header("Authorization");
			if (authHeader?.startsWith("Bearer ")) {
				const token = authHeader.slice(7);
				c.set("auth", {
					accessToken: token,
					source: "bearer",
				});
				return next();
			}
			return c.json({ error: "Missing or invalid Authorization header" }, 401);
		}

		// In managed mode, use stored credentials
		const credentials = await storage.load();
		if (!credentials) {
			return c.json(
				{
					error: "No OAuth credentials found. Please authenticate at /auth/login",
				},
				401,
			);
		}

		// Check if credentials are expired
		const now = Date.now();
		const buffer = 5 * 60 * 1000; // 5 minute buffer

		if (now > credentials.expiresAt - buffer) {
			logger.warn("OAuth token expired. Please re-authenticate at /auth/login");
			return c.json(
				{
					error: "Token expired. Please re-authenticate at /auth/login",
				},
				401,
			);
		}

		c.set("auth", {
			accessToken: credentials.accessToken,
			enterpriseUrl: credentials.enterpriseUrl,
			source: "managed",
		});

		await next();
	};
}

/**
 * Helper to get auth context from request
 */
export function getAuthContext(c: Context): AuthContext {
	const auth = c.get("auth");
	if (!auth) {
		throw new Error("Auth context not found");
	}
	return auth;
}
