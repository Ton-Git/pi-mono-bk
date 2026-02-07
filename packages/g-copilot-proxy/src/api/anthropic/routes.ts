/**
 * Anthropic-Compatible API Routes
 * /v1/messages - Claude messages with streaming support
 * /v1/models - List available models
 * /v1/models/{model_id} - Get specific model details
 */

import { zValidator } from "@hono/zod-validator";
import { Hono } from "hono";
import { streamText } from "hono/streaming";
import { v4 as uuidv4 } from "uuid";
import { getAuthContext } from "../../auth/middleware.js";
import type { Config } from "../../config.js";
import type { AnthropicMessageRequest } from "../../core/mapper-anthropic.js";
import {
	AnthropicMessageRequestSchema,
	streamFromPiAiEvent as anthropicStreamFromPiAiEvent,
	fromPiAiResponse,
	resolveModelAlias,
	toPiAiContext,
} from "../../core/mapper-anthropic.js";
import { getBridge } from "../../core/piai.js";
import { getLogger } from "../../logger.js";

const logger = getLogger();

export function createAnthropicRoutes(_config: Config) {
	const app = new Hono();
	const bridge = getBridge();

	/**
	 * GET /v1/models
	 * List available GitHub Copilot models in Anthropic format
	 */
	app.get("/models", async (c) => {
		const _auth = getAuthContext(c);

		try {
			const models = bridge.listModels();

			const anthropicModels = models.map((m) => ({
				id: m.id,
				name: m.name,
				description: m.description || "",
				context_window: m.contextWindow,
				type: "model" as const,
			}));

			return c.json({
				data: anthropicModels,
			});
		} catch (error) {
			logger.error("Failed to list models", { error });
			return c.json({ error: "Failed to list models" }, 500);
		}
	});

	/**
	 * GET /v1/models/:model_id
	 * Get details for a specific model
	 */
	app.get("/models/:model_id", async (c) => {
		const _auth = getAuthContext(c);
		const modelId = c.req.param("model_id");

		try {
			const resolvedId = resolveModelAlias(modelId);
			const model = bridge.getModel(resolvedId);

			return c.json({
				id: model.id,
				name: model.name,
				description: model.description || "",
				context_window: model.contextWindow,
				type: "model",
			});
		} catch (error) {
			logger.error("Model not found", { modelId, error });
			return c.json({ error: { message: "Model not found" } }, 404);
		}
	});

	/**
	 * POST /v1/messages
	 * Messages endpoint with streaming support
	 */
	app.post("/messages", zValidator("json", AnthropicMessageRequestSchema), async (c) => {
		const auth = getAuthContext(c);
		const request = c.req.valid("json") as AnthropicMessageRequest;

		// Resolve model alias
		const modelId = resolveModelAlias(request.model);

		// Convert to pi-ai context
		const context = toPiAiContext(request);

		// Generate request ID
		const requestId = uuidv4();

		logger.info("Anthropic message request", {
			requestId,
			model: modelId,
			stream: request.stream,
		});

		try {
			// Streaming response
			if (request.stream) {
				return streamText(c, async (stream) => {
					// Stream from pi-ai
					const completionStream = bridge.streamCompletion(modelId, context, { apiKey: auth.accessToken });

					for await (const event of completionStream) {
						const events = anthropicStreamFromPiAiEvent(event, requestId, request.model);

						for (const e of events) {
							if (e.data) {
								await stream.write(`event: ${e.event}\n`);
								await stream.write(`data: ${JSON.stringify(e.data)}\n\n`);
							}
						}
					}
				});
			}

			// Non-streaming response
			const piaiMessage = await bridge.complete(modelId, context, {
				apiKey: auth.accessToken,
			});

			const response = fromPiAiResponse(piaiMessage, requestId, request.model);

			logger.info("Anthropic message response", {
				requestId,
				inputTokens: response.usage.input_tokens,
				outputTokens: response.usage.output_tokens,
			});

			return c.json(response);
		} catch (error) {
			logger.error("Message error", { requestId, error });

			const errorMessage = error instanceof Error ? error.message : "An error occurred during completion";

			return c.json(
				{
					error: {
						type: "api_error",
						message: errorMessage,
					},
				},
				500,
			);
		}
	});

	return app;
}
