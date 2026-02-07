/**
 * Anthropic Mapper tests
 */

import { describe, it, expect } from 'vitest';
import {
  resolveModelAlias,
  toPiAiContext,
  fromPiAiResponse,
  AnthropicMessageRequestSchema,
  type AnthropicMessageRequest,
} from '../src/core/mapper-anthropic.js';

describe('Anthropic Mapper', () => {
  describe('resolveModelAlias', () => {
    it('should resolve claude-3-opus to claude-opus-4.5', () => {
      expect(resolveModelAlias('claude-3-opus')).toBe('claude-opus-4.5');
    });

    it('should resolve claude-3-sonnet to claude-sonnet-4.5', () => {
      expect(resolveModelAlias('claude-3-sonnet')).toBe('claude-sonnet-4.5');
    });

    it('should resolve claude-3-haiku to claude-haiku-4.5', () => {
      expect(resolveModelAlias('claude-3-haiku')).toBe('claude-haiku-4.5');
    });

    it('should return unknown models as-is', () => {
      expect(resolveModelAlias('unknown-model')).toBe('unknown-model');
    });
  });

  describe('toPiAiContext', () => {
    it('should convert simple user message', () => {
      const request: AnthropicMessageRequest = {
        model: 'claude-3-sonnet-20240229',
        max_tokens: 1024,
        messages: [{ role: 'user', content: 'Hello!' }],
      };

      const context = toPiAiContext(request);

      expect(context.messages).toHaveLength(1);
      expect(context.messages[0].role).toBe('user');
    });

    it('should convert system prompt', () => {
      const request: AnthropicMessageRequest = {
        model: 'claude-3-sonnet-20240229',
        max_tokens: 1024,
        messages: [{ role: 'user', content: 'Hello!' }],
        system: 'You are a helpful assistant.',
      };

      const context = toPiAiContext(request);

      expect(context.systemPrompt).toBe('You are a helpful assistant.');
    });

    it('should convert structured content', () => {
      const request: AnthropicMessageRequest = {
        model: 'claude-3-sonnet-20240229',
        max_tokens: 1024,
        messages: [
          {
            role: 'user',
            content: [
              { type: 'text', text: 'What is in this image?' },
              {
                type: 'image',
                source: {
                  type: 'base64',
                  media_type: 'image/png',
                  data: 'base64data',
                },
              },
            ],
          },
        ],
      };

      const context = toPiAiContext(request);

      expect(context.messages).toHaveLength(1);
      const userMsg = context.messages[0];
      expect(userMsg.role).toBe('user');
      expect(Array.isArray(userMsg.content)).toBe(true);
    });

    it('should convert tools', () => {
      const request: AnthropicMessageRequest = {
        model: 'claude-3-sonnet-20240229',
        max_tokens: 1024,
        messages: [{ role: 'user', content: 'Hello!' }],
        tools: [
          {
            name: 'get_weather',
            description: 'Get current weather',
            input_schema: {
              type: 'object',
              properties: {
                location: { type: 'string' },
              },
            },
          },
        ],
      };

      const context = toPiAiContext(request);

      expect(context.tools).toHaveLength(1);
      expect(context.tools?.[0]).toEqual({
        name: 'get_weather',
        description: 'Get current weather',
        parameters: {
          type: 'object',
          properties: {
            location: { type: 'string' },
          },
        },
      });
    });
  });

  describe('fromPiAiResponse', () => {
    it('should convert text response', () => {
      const piaiMessage = {
        role: 'assistant',
        content: [{ type: 'text', text: 'Hello!' }],
        stopReason: 'stop',
        usage: { input: 10, output: 5, cost: { total: 0.0001 } },
      };

      const response = fromPiAiResponse(piaiMessage, 'msg-123', 'claude-3-sonnet-20240229');

      expect(response.type).toBe('message');
      expect(response.role).toBe('assistant');
      expect(response.content).toHaveLength(1);
      expect(response.content[0]).toEqual({
        type: 'text',
        text: 'Hello!',
      });
      expect(response.stop_reason).toBe('end_turn');
      expect(response.usage.input_tokens).toBe(10);
      expect(response.usage.output_tokens).toBe(5);
    });

    it('should convert tool call response', () => {
      const piaiMessage = {
        role: 'assistant',
        content: [
          { type: 'text', text: 'Let me check the weather.' },
          {
            type: 'toolCall',
            id: 'toolu_123',
            name: 'get_weather',
            arguments: { location: 'London' },
          },
        ],
        stopReason: 'toolUse',
        usage: { input: 10, output: 5, cost: { total: 0.0001 } },
      };

      const response = fromPiAiResponse(piaiMessage, 'msg-123', 'claude-3-sonnet-20240229');

      expect(response.content).toHaveLength(2);
      expect(response.content[1]).toEqual({
        type: 'tool_use',
        id: 'toolu_123',
        name: 'get_weather',
        input: { location: 'London' },
      });
      expect(response.stop_reason).toBe('tool_use');
    });
  });

  describe('AnthropicMessageRequestSchema', () => {
    it('should validate valid request', () => {
      const request = {
        model: 'claude-3-sonnet-20240229',
        max_tokens: 1024,
        messages: [{ role: 'user', content: 'Hello!' }],
      };

      expect(() => AnthropicMessageRequestSchema.parse(request)).not.toThrow();
    });

    it('should require max_tokens', () => {
      const request = {
        model: 'claude-3-sonnet-20240229',
        messages: [{ role: 'user', content: 'Hello!' }],
      };

      expect(() => AnthropicMessageRequestSchema.parse(request)).toThrow();
    });

    it('should reject negative temperature', () => {
      const request = {
        model: 'claude-3-sonnet-20240229',
        max_tokens: 1024,
        messages: [{ role: 'user', content: 'Hello!' }],
        temperature: -0.5,
      };

      expect(() => AnthropicMessageRequestSchema.parse(request)).toThrow();
    });
  });
});
