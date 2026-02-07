/**
 * Credential storage - persists OAuth credentials to file system
 */

import { existsSync } from "node:fs";
import { mkdir, readFile, unlink, writeFile } from "node:fs/promises";
import { join } from "node:path";
import { getLogger } from "../logger.js";
import type { OAuthCredentials } from "./types.js";

const logger = getLogger();
const AUTH_FILENAME = "auth.json";
const AUTH_VERSION = 1;

export class CredentialStorage {
	private authFilePath: string;

	constructor(dataDir: string) {
		this.authFilePath = join(dataDir, AUTH_FILENAME);
	}

	/**
	 * Ensure data directory exists
	 */
	private async ensureDir(): Promise<void> {
		const dir = this.authFilePath.substring(0, this.authFilePath.lastIndexOf("/"));
		if (!existsSync(dir)) {
			await mkdir(dir, { recursive: true });
		}
	}

	/**
	 * Save OAuth credentials to disk
	 */
	async save(credentials: OAuthCredentials): Promise<void> {
		await this.ensureDir();

		const data = {
			version: AUTH_VERSION,
			credentials,
		};

		await writeFile(this.authFilePath, JSON.stringify(data, null, 2), "utf-8");
		logger.info("Credentials saved", { path: this.authFilePath });
	}

	/**
	 * Load OAuth credentials from disk
	 */
	async load(): Promise<OAuthCredentials | null> {
		if (!existsSync(this.authFilePath)) {
			return null;
		}

		try {
			const content = await readFile(this.authFilePath, "utf-8");
			const data = JSON.parse(content) as { version: number; credentials: OAuthCredentials };

			if (data.version !== AUTH_VERSION) {
				logger.warn("Invalid auth file version", { version: data.version });
				return null;
			}

			logger.info("Credentials loaded", { path: this.authFilePath });
			return data.credentials;
		} catch (error) {
			logger.error("Failed to load credentials", { error });
			return null;
		}
	}

	/**
	 * Check if credentials exist
	 */
	async exists(): Promise<boolean> {
		return existsSync(this.authFilePath);
	}

	/**
	 * Delete stored credentials
	 */
	async clear(): Promise<void> {
		if (await this.exists()) {
			await unlink(this.authFilePath);
			logger.info("Credentials cleared", { path: this.authFilePath });
		}
	}

	/**
	 * Check if stored credentials are expired
	 */
	async isExpired(): Promise<boolean> {
		const credentials = await this.load();
		if (!credentials) {
			return true;
		}
		// Add 5 minute buffer before expiration
		return Date.now() > credentials.expiresAt - 5 * 60 * 1000;
	}
}
