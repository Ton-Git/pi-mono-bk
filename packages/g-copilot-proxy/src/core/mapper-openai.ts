/**
 * OpenAI Mapper
 * Converts OpenAI API requests/responses to/from pi-ai format
 */

import type { AssistantMessage, Context, ImageContent, TextContent, Tool } from "@mariozechner/pi-ai";
import { z } from "zod";
import { getLogger } from "../logger.js";

const _logger = getLogger();

// ============================================================================
// OpenAPI Request Schemas
// ============================================================================

/**
 * OpenAI chat message role
 */
export const OpenAIRoleSchema = z.enum(["system", "user", "assistant", "tool"]);

/**
 * OpenAI message content (can be string or array of content blocks)
 */
export const OpenAIContentSchema = z.union([
	z.string(),
	z.array(
		z.union([
			z.object({
				type: z.literal("text"),
				text: z.string(),
			}),
			z.object({
				type: z.literal("image_url"),
				image_url: z.union([
					z.string(),
					z.object({
						url: z.string(),
					}),
				]),
			}),
		]),
	),
]);

/**
 * OpenAI tool call
 */
export const OpenAIToolCallSchema = z.object({
	id: z.string(),
	type: z.literal("function"),
	function: z.object({
		name: z.string(),
		arguments: z.string(),
	}),
});

/**
 * OpenAI message
 */
export const OpenAIMessageSchema = z.object({
	role: OpenAIRoleSchema,
	content: OpenAIContentSchema.optional(),
	tool_calls: z.array(OpenAIToolCallSchema).optional(),
	tool_call_id: z.string().optional(),
	name: z.string().optional(),
});

/**
 * OpenAI function/tool definition
 */
export const OpenAIFunctionSchema = z.object({
	name: z.string(),
	description: z.string().optional(),
	parameters: z.record(z.unknown()).optional(), // JSON Schema
});

export const OpenAIToolSchema = z.object({
	type: z.literal("function"),
	function: OpenAIFunctionSchema,
});

/**
 * OpenAI chat completion request
 */
export const OpenAIChatRequestSchema = z.object({
	model: z.string(),
	messages: z.array(OpenAIMessageSchema),
	stream: z.boolean().default(false),
	temperature: z.number().min(0).max(2).optional(),
	max_tokens: z.number().int().positive().optional(),
	max_completion_tokens: z.number().int().positive().optional(),
	top_p: z.number().min(0).max(1).optional(),
	tools: z.array(OpenAIToolSchema).optional(),
	tool_choice: z.union([z.enum(["auto", "none", "required"]), z.string()]).optional(),
	user: z.string().optional(),
});

export type OpenAIChatRequest = z.infer<typeof OpenAIChatRequestSchema>;
export type OpenAIMessage = z.infer<typeof OpenAIMessageSchema>;
export type OpenAIContent = z.infer<typeof OpenAIContentSchema>;

// ============================================================================
// OpenAI Response Schemas
// ============================================================================

/**
 * OpenAI usage information
 */
export const OpenAIUsageSchema = z.object({
	prompt_tokens: z.number().int(),
	completion_tokens: z.number().int(),
	total_tokens: z.number().int(),
});

/**
 * OpenAI chat completion response (non-streaming)
 */
export const OpenAIChatResponseSchema = z.object({
	id: z.string(),
	object: z.literal("chat.completion"),
	created: z.number().int(),
	model: z.string(),
	choices: z.array(
		z.object({
			index: z.number().int(),
			message: z.object({
				role: z.literal("assistant"),
				content: z.string().nullable(),
				tool_calls: z.array(OpenAIToolCallSchema).optional(),
			}),
			finish_reason: z.enum(["stop", "length", "tool_calls", "content_filter"]),
		}),
	),
	usage: OpenAIUsageSchema,
});

/**
 * OpenAI chat completion chunk (streaming)
 */
export const OpenAIChatChunkSchema = z.object({
	id: z.string(),
	object: z.literal("chat.completion.chunk"),
	created: z.number().int(),
	model: z.string(),
	choices: z.array(
		z.object({
			index: z.number().int(),
			delta: z.object({
				role: z.literal("assistant").optional(),
				content: z.string().optional(),
				tool_calls: z.array(z.unknown()).optional(),
			}),
			finish_reason: z.enum(["stop", "length", "tool_calls", "content_filter"]).nullable(),
		}),
	),
});

// ============================================================================
// Model Aliases
// ============================================================================

/**
 * Map OpenAI model IDs to GitHub Copilot models
 */
const MODEL_ALIASES: Record<string, string> = {
	// GPT-4 aliases -> Claude Sonnet 4.5
	"gpt-4": "claude-sonnet-4.5",
	"gpt-4-turbo": "claude-sonnet-4.5",
	"gpt-4o": "claude-sonnet-4.5",
	"gpt-4o-mini": "claude-haiku-4.5",

	// GPT-3.5 aliases -> GPT 4.1
	"gpt-3.5-turbo": "gpt-4.1",

	// Claude aliases (for backward compatibility)
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
 * Convert OpenAI content to pi-ai content blocks
 */
function convertContent(content: OpenAIContent): any {
	if (typeof content === "string") {
		return content;
	}

	const converted = content.map((block) => {
		if (block.type === "text") {
			return { type: "text" as const, text: block.text };
		} else if (block.type === "image_url") {
			const url = typeof block.image_url === "string" ? block.image_url : block.image_url.url;
			// Extract base64 data if data URL
			const match = url.match(/^data:([^;]+);base64,(.+)$/);
			if (match) {
				return { type: "image" as const, data: match[2], mimeType: match[1] };
			}
			return { type: "image" as const, data: url };
		}
		return { type: "text" as const, text: "" };
	});

	// Return single item if array has only one element
	return converted.length === 1 ? converted[0] : converted;
}

/**
 * Convert OpenAI tools to pi-ai tools
 */
function convertTools(openaiTools?: z.infer<typeof OpenAIToolSchema>[]): Tool[] | undefined {
	if (!openaiTools) return undefined;

	return openaiTools.map((tool) => ({
		name: tool.function.name,
		description: tool.function.description || "",
		parameters: tool.function.parameters as any,
	}));
}

/**
 * Convert OpenAI messages to pi-ai context
 */
export function toPiAiContext(request: OpenAIChatRequest): Context {
	const messages: Context["messages"] = [];

	for (const msg of request.messages) {
		switch (msg.role) {
			case "system":
				// System message is handled via systemPrompt in context
				break;

			case "user": {
				const content = convertContent(msg.content || "");
				messages.push({
					role: "user",
					content: [content as TextContent | ImageContent],
					timestamp: Date.now(),
				});
				break;
			}

			case "assistant": {
				const content = msg.content ? convertContent(msg.content) : "";
				const blocks: any[] = [];

				if (typeof content === "string" && content) {
					blocks.push({ type: "text", text: content });
				} else if (typeof content === "object" && content?.type === "text") {
					blocks.push(content);
				}

				// Add tool calls
				if (msg.tool_calls) {
					for (const tc of msg.tool_calls) {
						blocks.push({
							type: "toolCall",
							id: tc.id,
							name: tc.function.name,
							arguments: JSON.parse(tc.function.arguments),
						});
					}
				}

				messages.push({
					role: "assistant",
					content: blocks,
				} as any);
				break;
			}

			case "tool": {
				const content = msg.content ? convertContent(msg.content) : "";
				messages.push({
					role: "toolResult",
					toolCallId: msg.tool_call_id || "",
					toolName: msg.name || "",
					content: [content as TextContent],
					isError: false,
					timestamp: Date.now(),
				});
				break;
			}
		}
	}

	// Extract system message
	const systemMsg = request.messages.find((m) => m.role === "system");
	const systemPrompt = systemMsg?.content
		? typeof systemMsg.content === "string"
			? systemMsg.content
			: (systemMsg.content as any[]).find((b) => b.type === "text")?.text || ""
		: undefined;

	const tools = convertTools(request.tools);

	return {
		systemPrompt,
		messages,
		tools,
	};
}

/**
 * Convert pi-ai assistant message to OpenAI chat completion response
 */
export function fromPiAiResponse(
	piaiMessage: AssistantMessage,
	requestId: string,
	model: string,
	created: number,
): z.infer<typeof OpenAIChatResponseSchema> {
	const contentBlocks: string[] = [];
	const toolCalls: z.infer<typeof OpenAIToolCallSchema>[] = [];

	for (const block of piaiMessage.content) {
		if (block.type === "text") {
			contentBlocks.push(block.text);
		} else if (block.type === "toolCall") {
			toolCalls.push({
				id: block.id,
				type: "function",
				function: {
					name: block.name,
					arguments: JSON.stringify(block.arguments),
				},
			});
		}
		// Thinking blocks are typically not exposed in OpenAI format
	}

	// Map stop reason
	const finishReasonMap: Record<string, "stop" | "length" | "tool_calls" | "content_filter"> = {
		stop: "stop",
		length: "length",
		toolUse: "tool_calls",
		error: "stop",
	};

	return {
		id: requestId,
		object: "chat.completion",
		created,
		model,
		choices: [
			{
				index: 0,
				message: {
					role: "assistant",
					content: contentBlocks.length > 0 ? contentBlocks.join("") : null,
					tool_calls: toolCalls.length > 0 ? toolCalls : undefined,
				},
				finish_reason: finishReasonMap[piaiMessage.stopReason] || "stop",
			},
		],
		usage: {
			prompt_tokens: piaiMessage.usage.input,
			completion_tokens: piaiMessage.usage.output,
			total_tokens: piaiMessage.usage.input + piaiMessage.usage.output,
		},
	};
}

/**
 * Convert pi-ai stream event to OpenAI chat completion chunk
 */
export function* streamFromPiAiEvent(
	event: unknown,
	requestId: string,
	model: string,
	created: number,
): Generator<z.infer<typeof OpenAIChatChunkSchema>> {
	const e = event as {
		type: string;
		delta?: string;
		contentIndex?: number;
		content?: { text?: string; toolCallId?: string; name?: string; arguments?: string; id?: string };
		toolCall?: { id: string; name: string; arguments: Record<string, unknown> };
		reason?: string;
	};

	if (e.type === "text_delta" && e.delta) {
		yield {
			id: requestId,
			object: "chat.completion.chunk",
			created,
			model,
			choices: [
				{
					index: e.contentIndex || 0,
					delta: {
						content: e.delta,
					},
					finish_reason: null,
				},
			],
		};
	} else if (e.type === "toolcall_end" && e.toolCall) {
		yield {
			id: requestId,
			object: "chat.completion.chunk",
			created,
			model,
			choices: [
				{
					index: e.contentIndex || 0,
					delta: {
						tool_calls: [
							{
								index: 0,
								id: e.toolCall.id,
								type: "function",
								function: {
									name: e.toolCall.name,
									arguments: JSON.stringify(e.toolCall.arguments),
								},
							},
						],
					},
					finish_reason: null,
				},
			],
		};
	} else if (e.type === "done") {
		const finishReasonMap: Record<string, "stop" | "length" | "tool_calls"> = {
			stop: "stop",
			length: "length",
			toolUse: "tool_calls",
		};

		yield {
			id: requestId,
			object: "chat.completion.chunk",
			created,
			model,
			choices: [
				{
					index: 0,
					delta: {},
					finish_reason: finishReasonMap[e.reason || "stop"] || "stop",
				},
			],
		};
	}
}
