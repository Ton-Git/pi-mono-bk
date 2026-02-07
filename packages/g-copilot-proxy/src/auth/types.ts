/**
 * Authentication types and interfaces
 */

/**
 * OAuth credentials stored from GitHub Copilot login
 */
export interface OAuthCredentials {
	/** Access token for API calls */
	accessToken: string;
	/** Refresh token for getting new access tokens */
	refreshToken: string;
	/** Token expiration timestamp (milliseconds since epoch) */
	expiresAt: number;
	/** Optional GitHub Enterprise URL */
	enterpriseUrl?: string;
	/** When credentials were stored */
	createdAt: number;
}

/**
 * Authentication state returned by status endpoint
 */
export interface AuthStatus {
	mode: "passthrough" | "managed";
	authenticated: boolean;
	enterpriseUrl?: string | null;
}

/**
 * Login request options
 */
export interface LoginOptions {
	/** Optional GitHub Enterprise URL */
	enterpriseUrl?: string;
}

/**
 * Login response
 */
export interface LoginResponse {
	status: "started" | "pending" | "complete" | "error";
	message: string;
	deviceCode?: string;
	userCode?: string;
	verificationUri?: string;
}

/**
 * Callback for OAuth authentication events
 */
export interface AuthCallbacks {
	/** Called when the verification URL is available */
	onAuth?: (url: string, instructions?: string) => void;
	/** Called for progress updates */
	onProgress?: (message: string) => void;
}
