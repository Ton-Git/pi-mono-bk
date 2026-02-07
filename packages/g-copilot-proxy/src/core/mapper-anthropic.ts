/**
 * Anthropic Mapper
 * Converts Anthropic API requests/responses to/from pi-ai format
 */

import type { AssistantMessage, Context, Tool } from "@mariozechner/pi-ai";
import { z } from "zod";
import { getLogger } from "../logger.js";

const _logger = getLogger();

// ============================================================================
// Anthropic Request Schemas
// ============================================================================

/**
 * Anthropic message role
 */
export const AnthropicRoleSchema = z.enum(["user", "assistant"]);

/**
 * Anthropic content block types
 */
export const AnthropicContentBlockSchema = z.union([
	z.object({
		type: z.literal("text"),
		text: z.string(),
	}),
	z.object({
		type: z.literal("image"),
		source: z.object({
			type: z.literal("base64"),
			media_type: z.string(),
			data: z.string(),
		}),
	}),
	z.object({
		type: z.literal("tool_use"),
		id: z.string(),
		name: z.string(),
		input: z.record(z.unknown()),
	}),
	z.object({
		type: z.literal("tool_result"),
		tool_use_id: z.string(),
		content: z.union([z.string(), z.array(z.any())]),
		is_error: z.boolean().optional(),
	}),
]);

/**
 * Anthropic message
 */
export const AnthropicMessageSchema = z.object({
	role: AnthropicRoleSchema,
	content: z.union([z.string(), z.array(AnthropicContentBlockSchema)]),
});

/**
 * Anthropic tool definition
 */
export const AnthropicToolSchema = z.object({
	name: z.string(),
	description: z.string(),
	input_schema: z.record(z.unknown()), // JSON Schema
});

/**
 * Anthropic message request
 */
export const AnthropicMessageRequestSchema = z.object({
	model: z.string(),
	max_tokens: z.number().int().positive(),
	messages: z.array(AnthropicMessageSchema),
	system: z.string().optional(),
	temperature: z.number().min(0).max(1).optional(),
	top_p: z.number().min(0).max(1).optional(),
	tools: z.array(AnthropicToolSchema).optional(),
	stream: z.boolean().default(false),
});

export type AnthropicMessageRequest = z.infer<typeof AnthropicMessageRequestSchema>;
export type AnthropicMessage = z.infer<typeof AnthropicMessageSchema>;
export type AnthropicContentBlock = z.infer<typeof AnthropicContentBlockSchema>;

// ============================================================================
// Anthropic Response Schemas
// ============================================================================

/**
 * Anthropic usage information
 */
export const AnthropicUsageSchema = z.object({
	input_tokens: z.number().int(),
	output_tokens: z.number().int(),
});

/**
 * Anthropic message response (non-streaming)
 */
export const AnthropicMessageResponseSchema = z.object({
	id: z.string(),
	type: z.literal("message"),
	role: z.literal("assistant"),
	content: z.array(z.any()),
	model: z.string(),
	stop_reason: z.enum(["end_turn", "max_tokens", "stop_sequence", "tool_use"]),
	usage: AnthropicUsageSchema,
});

// ============================================================================
// Model Aliases
// ============================================================================

/**
 * Map Anthropic model IDs to GitHub Copilot models
 */
const MODEL_ALIASES: Record<string, string> = {
	// Claude 3 aliases
	"claude-3-opus-20240229": "claude-opus-4.5",
	"claude-3-sonnet-20240229": "claude-sonnet-4.5",
	"claude-3-5-sonnet-20240620": "claude-sonnet-4.5",
	"claude-3-haiku-20240307": "claude-haiku-4.5",
	"claude-3-opus": "claude-opus-4.5",
	"claude-3-sonnet": "claude-sonnet-4.5",
	"claude-3-haiku": "claude-haiku-4.5",
};

/**
 * Resolve model alias to actual GitHub Copilot model ID
 */
export function resolveModelAlias(model: string): string {
	return MODEL_ALIASES[model] || model;
}

// ============================================================================
// Conversion Functions
// ============================================================================

/**
 * Convert Anthropic tools to pi-ai tools
 */
function convertTools(anthropicTools?: z.infer<typeof AnthropicToolSchema>[]): Tool[] | undefined {
	if (!anthropicTools) return undefined;

	return anthropicTools.map((tool) => ({
		name: tool.name,
		description: tool.description,
		parameters: tool.input_schema as any,
	}));
}

/**
 * Convert Anthropic messages to pi-ai context
 */
export function toPiAiContext(request: AnthropicMessageRequest): Context {
	const messages: any[] = [];

	for (const msg of request.messages) {
		if (msg.role === "user") {
			const content =
				typeof msg.content === "string"
					? [{ type: "text", text: msg.content }]
					: msg.content.map((block: any) => {
							if (block.type === "text") {
								return { type: "text", text: block.text };
							} else if (block.type === "image") {
								return {
									type: "image",
									data: block.source.data,
									mimeType: block.source.media_type,
								};
							} else if (block.type === "tool_use") {
								return {
									type: "toolCall",
									id: block.id,
									name: block.name,
									arguments: block.input,
								};
							}
							return { type: "text", text: "" };
						});

			messages.push({
				role: "user",
				content,
				timestamp: Date.now(),
			});
		} else if (msg.role === "assistant") {
			const content =
				typeof msg.content === "string"
					? [{ type: "text", text: msg.content }]
					: msg.content.map((block: any) => {
							if (block.type === "text") {
								return { type: "text", text: block.text };
							} else if (block.type === "tool_use") {
								return {
									type: "toolCall",
									id: block.id,
									name: block.name,
									arguments: block.input,
								};
							}
							return { type: "text", text: "" };
						});

			messages.push({
				role: "assistant",
				content,
			} as any);
		}
	}

	const tools = convertTools(request.tools);

	return {
		systemPrompt: request.system,
		messages,
		tools,
	};
}

/**
 * Convert pi-ai assistant message to Anthropic message response
 */
export function fromPiAiResponse(
	piaiMessage: AssistantMessage,
	requestId: string,
	model: string,
): z.infer<typeof AnthropicMessageResponseSchema> {
	const content: any[] = [];

	for (const block of piaiMessage.content) {
		if (block.type === "text") {
			content.push({
				type: "text",
				text: block.text,
			});
		} else if (block.type === "toolCall") {
			content.push({
				type: "tool_use",
				id: (block as any).id,
				name: block.name,
				input: block.arguments,
			});
		}
	}

	// Map stop reason
	const stopReasonMap: Record<string, "end_turn" | "max_tokens" | "stop_sequence" | "tool_use"> = {
		stop: "end_turn",
		length: "max_tokens",
		toolUse: "tool_use",
		error: "end_turn",
	};

	return {
		id: requestId,
		type: "message",
		role: "assistant",
		content,
		model,
		stop_reason: stopReasonMap[piaiMessage.stopReason] || "end_turn",
		usage: {
			input_tokens: piaiMessage.usage.input,
			output_tokens: piaiMessage.usage.output,
		},
	};
}

/**
 * Convert pi-ai stream event to Anthropic streaming format
 */
export function* streamFromPiAiEvent(
	event: unknown,
	requestId: string,
	model: string,
): Generator<{ event: string; data?: unknown }> {
	const e = event as {
		type: string;
		delta?: string;
		contentIndex?: number;
		content?: any;
		toolCall?: any;
		message?: AssistantMessage;
		reason?: string;
	};

	// Send message_start
	if (e.type === "start" && e.message) {
		yield {
			event: "message_start",
			data: {
				id: requestId,
				type: "message",
				role: "assistant",
				content: [],
				model,
				stop_reason: null,
				usage: { input_tokens: 0, output_tokens: 0 },
			},
		};
	}

	// Text content
	if (e.type === "text_delta" && e.delta) {
		yield {
			event: "content_block_delta",
			data: {
				type: "content_block_delta",
				index: e.contentIndex || 0,
				delta: { type: "text_delta", text: e.delta },
			},
		};
	}

	// Tool call
	if (e.type === "toolcall_end" && e.toolCall) {
		yield {
			event: "content_block_stop",
			data: {
				type: "content_block_stop",
				index: e.contentIndex || 0,
			},
		};
	}

	// Message complete
	if (e.type === "done" && e.message) {
		yield {
			event: "message_delta",
			data: {
				type: "message_delta",
				delta: {},
				usage: {
					output_tokens: e.message.usage.output,
				},
			},
		};

		const stopReasonMap: Record<string, "end_turn" | "max_tokens" | "tool_use"> = {
			stop: "end_turn",
			length: "max_tokens",
			toolUse: "tool_use",
		};

		yield {
			event: "message_stop",
			data: {
				type: "message_stop",
				stop_reason: stopReasonMap[e.reason || "stop"] || "end_turn",
			},
		};
	}
}
