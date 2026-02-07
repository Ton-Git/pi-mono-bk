/**
 * pi-ai Bridge - Direct imports from @mariozechner/pi-ai
 * No subprocess needed!
 */

import type {
	AssistantMessage,
	Context,
	ImageContent,
	Message,
	StreamOptions,
	TextContent,
	ThinkingContent,
	Tool,
	ToolCall,
} from "@mariozechner/pi-ai";
import { complete, getModel, getModels, stream } from "@mariozechner/pi-ai";
import { getLogger } from "../logger.js";

const logger = getLogger();

/**
 * SSE event for streaming responses
 */
export interface SSEEvent {
	event: string;
	data: unknown;
}

/**
 * Pi-ai bridge - provides direct access to pi-ai functions
 */
export class PiAiBridge {
	private provider = "github-copilot" as const;

	/**
	 * Get a model from pi-ai
	 */
	getModel(modelId: string): any {
		return getModel(this.provider, modelId as any);
	}

	/**
	 * List all available GitHub Copilot models
	 */
	listModels(): any[] {
		return getModels(this.provider);
	}

	/**
	 * Stream a completion request
	 */
	async *streamCompletion(modelId: string, context: Context, options: StreamOptions = {}): AsyncGenerator<SSEEvent> {
		const model = this.getModel(modelId);

		logger.debug("Starting stream", { model: modelId, provider: this.provider });

		try {
			const streamGenerator = stream(model, context, options as any);

			for await (const event of streamGenerator) {
				// Convert pi-ai events to SSE format
				const e = event as {
					type: string;
					partial?: AssistantMessage;
					contentIndex?: number;
					delta?: string;
					content?: string | TextContent | ImageContent | ToolCall | ThinkingContent;
					toolCall?: ToolCall;
					reason?: string;
					error?: Error;
					message?: AssistantMessage;
				};

				switch (e.type) {
					case "start":
						yield { event: "start", data: e.partial };
						break;

					case "text_start":
						yield { event: "text_start", data: { contentIndex: e.contentIndex } };
						break;

					case "text_delta":
						yield {
							event: "text_delta",
							data: { delta: e.delta, contentIndex: e.contentIndex },
						};
						break;

					case "text_end":
						yield {
							event: "text_end",
							data: {
								text: typeof e.content === "string" ? e.content : (e.content as TextContent).text,
								contentIndex: e.contentIndex,
							},
						};
						break;

					case "thinking_start":
						yield { event: "thinking_start", data: { contentIndex: e.contentIndex } };
						break;

					case "thinking_delta":
						yield {
							event: "thinking_delta",
							data: {
								delta: typeof e.content === "string" ? e.content : (e.content as ThinkingContent).thinking,
								contentIndex: e.contentIndex,
							},
						};
						break;

					case "thinking_end":
						yield {
							event: "thinking_end",
							data: {
								thinking: typeof e.content === "string" ? e.content : (e.content as ThinkingContent).thinking,
								contentIndex: e.contentIndex,
							},
						};
						break;

					case "toolcall_start":
						yield { event: "toolcall_start", data: { contentIndex: e.contentIndex } };
						break;

					case "toolcall_delta":
						yield {
							event: "toolcall_delta",
							data: {
								delta: e.delta,
								contentIndex: e.contentIndex,
								partial: e.partial,
							},
						};
						break;

					case "toolcall_end":
						yield {
							event: "toolcall_end",
							data: { toolCall: e.toolCall, contentIndex: e.contentIndex },
						};
						break;

					case "done":
						yield { event: "done", data: { reason: e.reason, message: e.message } };
						break;

					case "error":
						yield { event: "error", data: { reason: e.reason, error: e.error } };
						break;

					default:
						logger.debug("Unknown event type", { type: e.type });
				}
			}
		} catch (error) {
			logger.error("Stream error", { error });
			yield {
				event: "error",
				data: { error: error instanceof Error ? error.message : "Unknown error" },
			};
		}
	}

	/**
	 * Get a complete (non-streaming) response
	 */
	async complete(modelId: string, context: Context, options: StreamOptions = {}): Promise<AssistantMessage> {
		const model = this.getModel(modelId);

		logger.debug("Starting completion", { model: modelId, provider: this.provider });

		try {
			return await complete(model, context, options as any);
		} catch (error) {
			logger.error("Completion error", { error });
			throw error;
		}
	}
}

// Singleton instance
let bridgeInstance: PiAiBridge | null = null;

/**
 * Get or create the global pi-ai bridge instance
 */
export function getBridge(): PiAiBridge {
	if (!bridgeInstance) {
		bridgeInstance = new PiAiBridge();
	}
	return bridgeInstance;
}

/**
 * Reset bridge (useful for testing)
 */
export function resetBridge(): void {
	bridgeInstance = null;
}

// Re-export types from pi-ai for convenience
export type { Context, Tool, AssistantMessage, Message };
