/**
 * GitHub Copilot OAuth integration using @mariozechner/pi-ai
 * Direct imports - no subprocess needed!
 */

import { loginGitHubCopilot } from "@mariozechner/pi-ai";
import { getLogger } from "../logger.js";
import type { AuthCallbacks, LoginOptions, LoginResponse } from "./types.js";

const logger = getLogger();

/**
 * GitHub Copilot OAuth Manager
 * Uses pi-ai's loginGitHubCopilot function directly
 */
export class OAuthManager {
	private pendingLogins = new Map<string, LoginResponse>();

	/**
	 * Initiate GitHub Copilot OAuth login
	 * Returns immediately with verification URL and code when available
	 */
	async login(options: LoginOptions = {}, callbacks: AuthCallbacks = {}): Promise<LoginResponse> {
		// Create a promise that resolves when onAuth is called
		let resolveAuth: ((data: { url: string; userCode: string; deviceCode?: string }) => void) | null = null;
		const authDataPromise = new Promise<{ url: string; userCode: string; deviceCode?: string }>((resolve) => {
			resolveAuth = resolve;
		});

		// Generate a unique ID for this login attempt
		const loginId = `login-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;

		// Initialize pending state
		const response: LoginResponse = {
			status: "pending",
			message: "OAuth flow initiated",
		};
		this.pendingLogins.set(loginId, response);

		// Start OAuth flow in background
		this.performLogin(loginId, options, { ...callbacks, onAuth: async (url, instructions) => {
			// Extract user code from instructions
			let userCode = "";
			let deviceCode = "";
			if (instructions?.includes("code:")) {
				const match = instructions.match(/code:\s*([A-Z0-9-]+)/i);
				if (match) {
					userCode = match[1];
					deviceCode = match[1];
				}
			}

			// Resolve the promise so login() can return
			resolveAuth?.({ url, userCode, deviceCode });

			// Update pending state
			const current = this.pendingLogins.get(loginId);
			if (current) {
				current.verificationUri = url;
				current.userCode = userCode;
				current.deviceCode = deviceCode;
				current.status = "pending";
			}

			callbacks.onAuth?.(url, instructions);
		}});

		// Wait for auth data to be available
		const authData = await authDataPromise;

		return {
			status: "pending",
			message: "Please authenticate with the provided code",
			verificationUri: authData.url,
			userCode: authData.userCode,
			deviceCode: authData.deviceCode,
		};
	}

	/**
	 * Perform the actual OAuth login flow
	 */
	private async performLogin(loginId: string, options: LoginOptions, callbacks: AuthCallbacks): Promise<void> {
		try {
			logger.info("Starting GitHub Copilot OAuth flow...");

			const _credentials = await loginGitHubCopilot({
				onAuth: (url: string, instructions?: string) => {
					logger.info(`Auth URL: ${url}`);
					if (instructions) {
						logger.info(`Instructions: ${instructions}`);
					}

					// Update pending state
					const current = this.pendingLogins.get(loginId);
					if (current) {
						current.verificationUri = url;
						current.status = "pending";
						if (instructions?.includes("code:")) {
							const match = instructions.match(/code:\s*([A-Z0-9-]+)/i);
							if (match) {
								current.userCode = match[1];
								current.deviceCode = match[1];
							}
						}
					}

					callbacks.onAuth?.(url, instructions);
				},
				onPrompt: async (prompt: { message: string }) => {
					logger.debug("OAuth prompt", { message: prompt.message });
					// For enterprise URL prompt
					return options.enterpriseUrl || "";
				},
				onProgress: (message: string) => {
					logger.info(`OAuth progress: ${message}`);
					callbacks.onProgress?.(message);
				},
			});

			// Update state to complete
			const current = this.pendingLogins.get(loginId);
			if (current) {
				current.status = "complete";
				current.message = "Login successful!";
			}

			logger.info("OAuth login successful");
		} catch (error) {
			logger.error("OAuth login failed", { error });

			const current = this.pendingLogins.get(loginId);
			if (current) {
				current.status = "error";
				current.message = error instanceof Error ? error.message : "Unknown error";
			}
		}
	}

	/**
	 * Get the status of a pending login
	 */
	getLoginStatus(loginId: string): LoginResponse | undefined {
		return this.pendingLogins.get(loginId);
	}

	/**
	 * Clean up old pending logins
	 */
	cleanup(loginsOlderThanMs: number = 5 * 60 * 1000): void {
		const cutoff = Date.now() - loginsOlderThanMs;
		for (const [id, _login] of this.pendingLogins.entries()) {
			// Extract timestamp from ID (format: login-TIMESTAMP-random)
			const match = id.match(/login-(\d+)-/);
			if (match) {
				const timestamp = parseInt(match[1], 10);
				if (timestamp < cutoff) {
					this.pendingLogins.delete(id);
				}
			}
		}
	}
}

// Singleton instance
let oauthManagerInstance: OAuthManager | null = null;

/**
 * Get or create the global OAuth manager instance
 */
export function getOAuthManager(): OAuthManager {
	if (!oauthManagerInstance) {
		oauthManagerInstance = new OAuthManager();
	}
	return oauthManagerInstance;
}

/**
 * Reset OAuth manager (useful for testing)
 */
export function resetOAuthManager(): void {
	oauthManagerInstance = null;
}
