/**
 * Configuration management for g-copilot-proxy
 * Loads settings from environment variables with sensible defaults
 */

import { config } from "dotenv";
import { z } from "zod";

// Load environment variables from .env file (if it exists)
// Note: This runs once when the module is first imported
// Tests should set environment variables before importing this module
if (process.env.NODE_ENV !== "test") {
	config();
}

/**
 * Schema for environment-based configuration
 */
const ConfigSchema = z.object({
	// Server settings
	PORT: z.string().default("8000").transform(Number),
	HOST: z.string().default("0.0.0.0"),

	// Authentication
	AUTH_MODE: z.enum(["passthrough", "managed"]).default("managed"),
	GITHUB_ENTERPRISE_URL: z.string().optional(),

	// CORS
	CORS_ORIGINS: z
		.string()
		.default("*")
		.transform((val) => (val === "*" ? ["*"] : val.split(",").map((s) => s.trim()))),

	// Logging
	LOG_LEVEL: z.enum(["debug", "info", "warn", "error"]).default("info"),

	// Data directory
	DATA_DIR: z.string().default("./data"),

	// pi-ai settings
	PIAI_CACHE_RETENTION: z.enum(["default", "long"]).default("default"),
});

/**
 * Parsed configuration type
 */
export type Config = z.infer<typeof ConfigSchema>;

/**
 * Load and validate configuration from environment
 */
export function loadConfig(): Config {
	const result = ConfigSchema.safeParse(process.env);

	if (!result.success) {
		const errors = result.error.errors.map((e) => `  ${e.path.join(".")}: ${e.message}`).join("\n");
		throw new Error(`Invalid configuration:\n${errors}`);
	}

	return result.data;
}

/**
 * Global configuration instance
 */
let configInstance: Config | null = null;

/**
 * Get or create the global configuration instance
 */
export function getConfig(): Config {
	if (!configInstance) {
		configInstance = loadConfig();
	}
	return configInstance;
}

/**
 * Reset configuration (useful for testing)
 */
export function resetConfig(): void {
	configInstance = null;
}
