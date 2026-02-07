/**
 * OpenAI-Compatible API Routes
 * /v1/chat/completions - Chat completions with streaming support
 * /v1/models - List available models
 * /v1/models/{model_id} - Get specific model details
 */

import { zValidator } from "@hono/zod-validator";
import { Hono } from "hono";
import { streamText } from "hono/streaming";
import { v4 as uuidv4 } from "uuid";
import { getAuthContext } from "../../auth/middleware.js";
import type { Config } from "../../config.js";
import type { OpenAIChatRequest } from "../../core/mapper-openai.js";
import {
	fromPiAiResponse,
	OpenAIChatRequestSchema,
	resolveModelAlias,
	streamFromPiAiEvent,
	toPiAiContext,
} from "../../core/mapper-openai.js";
import { getBridge } from "../../core/piai.js";
import { getLogger } from "../../logger.js";

const logger = getLogger();

export function createOpenAIRoutes(_config: Config) {
	const app = new Hono();
	const bridge = getBridge();

	/**
	 * GET /v1/models
	 * List available GitHub Copilot models in OpenAI format
	 */
	app.get("/models", async (c) => {
		const _auth = getAuthContext(c);

		try {
			const models = bridge.listModels();

			const openaiModels = models.map((m) => ({
				id: m.id,
				object: "model",
				created: Math.floor(Date.now() / 1000),
				owned_by: "github-copilot",
			}));

			return c.json({
				object: "list",
				data: openaiModels,
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
				object: "model",
				created: Math.floor(Date.now() / 1000),
				owned_by: "github-copilot",
			});
		} catch (error) {
			logger.error("Model not found", { modelId, error });
			return c.json({ error: "Model not found" }, 404);
		}
	});

	/**
	 * POST /v1/chat/completions
	 * Chat completions endpoint with streaming support
	 */
	app.post("/chat/completions", zValidator("json", OpenAIChatRequestSchema), async (c) => {
		const auth = getAuthContext(c);
		const request = c.req.valid("json") as OpenAIChatRequest;

		// Resolve model alias
		const modelId = resolveModelAlias(request.model);

		// Convert to pi-ai context
		const context = toPiAiContext(request);

		// Generate request metadata
		const requestId = uuidv4();
		const created = Math.floor(Date.now() / 1000);

		logger.info("OpenAI chat completion request", {
			requestId,
			model: modelId,
			stream: request.stream,
		});

		try {
			// Streaming response
			if (request.stream) {
				return streamText(c, async (stream) => {
					// Send initial chunk
					await stream.write(
						`data: ${JSON.stringify({
							id: requestId,
							object: "chat.completion.chunk",
							created,
							model: request.model,
							choices: [{ index: 0, delta: { role: "assistant" }, finish_reason: null }],
						})}\n\n`,
					);

					// Stream from pi-ai
					const completionStream = bridge.streamCompletion(modelId, context, { apiKey: auth.accessToken });

					for await (const event of completionStream) {
						const chunks = streamFromPiAiEvent(event, requestId, request.model, created);

						for (const chunk of chunks) {
							await stream.write(`data: ${JSON.stringify(chunk)}\n\n`);
						}
					}

					// Send final chunk
					await stream.write(`data: [DONE]\n\n`);
				});
			}

			// Non-streaming response
			const piaiMessage = await bridge.complete(modelId, context, {
				apiKey: auth.accessToken,
			});

			const response = fromPiAiResponse(piaiMessage, requestId, request.model, created);

			logger.info("OpenAI chat completion response", {
				requestId,
				promptTokens: response.usage.prompt_tokens,
				completionTokens: response.usage.completion_tokens,
			});

			return c.json(response);
		} catch (error) {
			logger.error("Chat completion error", { requestId, error });

			const errorMessage = error instanceof Error ? error.message : "An error occurred during completion";

			return c.json(
				{
					error: {
						message: errorMessage,
						type: "api_error",
						code: "internal_error",
					},
				},
				500,
			);
		}
	});

	return app;
}
