/**
 * Logger utility
 * Simple console-based logging with levels
 */

import type { Config } from "./config.js";

export type LogLevel = "debug" | "info" | "warn" | "error";

const LOG_LEVELS: Record<LogLevel, number> = {
	debug: 0,
	info: 1,
	warn: 2,
	error: 3,
};

class Logger {
	private level: number;

	constructor(level: LogLevel) {
		this.level = LOG_LEVELS[level];
	}

	private shouldLog(level: LogLevel): boolean {
		return LOG_LEVELS[level] >= this.level;
	}

	private formatMessage(level: LogLevel, message: string, meta?: unknown): string {
		const timestamp = new Date().toISOString();
		const prefix = `[${timestamp}] [${level.toUpperCase()}]`;
		if (meta) {
			return `${prefix} ${message} ${JSON.stringify(meta)}`;
		}
		return `${prefix} ${message}`;
	}

	debug(message: string, meta?: unknown): void {
		if (this.shouldLog("debug")) {
			console.debug(this.formatMessage("debug", message, meta));
		}
	}

	info(message: string, meta?: unknown): void {
		if (this.shouldLog("info")) {
			console.info(this.formatMessage("info", message, meta));
		}
	}

	warn(message: string, meta?: unknown): void {
		if (this.shouldLog("warn")) {
			console.warn(this.formatMessage("warn", message, meta));
		}
	}

	error(message: string, meta?: unknown): void {
		if (this.shouldLog("error")) {
			console.error(this.formatMessage("error", message, meta));
		}
	}

	setLevel(level: LogLevel): void {
		this.level = LOG_LEVELS[level];
	}
}

let loggerInstance: Logger | null = null;

/**
 * Get or create the global logger instance
 */
export function getLogger(level?: LogLevel): Logger {
	if (!loggerInstance) {
		loggerInstance = new Logger(level || "info");
	}
	return loggerInstance;
}

/**
 * Initialize logger from configuration
 */
export function initLogger(config: Pick<Config, "LOG_LEVEL">): Logger {
	const logger = getLogger();
	logger.setLevel(config.LOG_LEVEL);
	return logger;
}

/**
 * Reset logger (useful for testing)
 */
export function resetLogger(): void {
	loggerInstance = null;
}
