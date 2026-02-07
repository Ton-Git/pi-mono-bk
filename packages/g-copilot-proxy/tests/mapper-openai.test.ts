/**
 * OpenAI Mapper tests
 */

import { describe, it, expect } from 'vitest';
import {
  resolveModelAlias,
  toPiAiContext,
  fromPiAiResponse,
  streamFromPiAiEvent,
  OpenAIChatRequestSchema,
  type OpenAIChatRequest,
} from '../src/core/mapper-openai.js';

describe('OpenAI Mapper', () => {
  describe('resolveModelAlias', () => {
    it('should resolve gpt-4 to claude-sonnet-4.5', () => {
      expect(resolveModelAlias('gpt-4')).toBe('claude-sonnet-4.5');
    });

    it('should resolve gpt-4o to claude-sonnet-4.5', () => {
      expect(resolveModelAlias('gpt-4o')).toBe('claude-sonnet-4.5');
    });

    it('should resolve gpt-4o-mini to claude-haiku-4.5', () => {
      expect(resolveModelAlias('gpt-4o-mini')).toBe('claude-haiku-4.5');
    });

    it('should resolve gpt-3.5-turbo to gpt-4.1', () => {
      expect(resolveModelAlias('gpt-3.5-turbo')).toBe('gpt-4.1');
    });

    it('should return unknown models as-is', () => {
      expect(resolveModelAlias('unknown-model')).toBe('unknown-model');
    });
  });

  describe('toPiAiContext', () => {
    it('should convert simple user message', () => {
      const request: OpenAIChatRequest = {
        model: 'gpt-4',
        messages: [{ role: 'user', content: 'Hello!' }],
      };

      const context = toPiAiContext(request);

      expect(context.messages).toHaveLength(1);
      expect(context.messages[0].role).toBe('user');
      // pi-ai Context expects content as array of objects or string
      expect(Array.isArray(context.messages[0].content) || typeof context.messages[0].content === 'string').toBe(true);
    });

    it('should convert system prompt', () => {
      const request: OpenAIChatRequest = {
        model: 'gpt-4',
        messages: [
          { role: 'system', content: 'You are a helpful assistant.' },
          { role: 'user', content: 'Hello!' },
        ],
      };

      const context = toPiAiContext(request);

      expect(context.systemPrompt).toBe('You are a helpful assistant.');
    });

    it('should convert assistant message with tool calls', () => {
      const request: OpenAIChatRequest = {
        model: 'gpt-4',
        messages: [
          { role: 'user', content: 'What is the weather?' },
          {
            role: 'assistant',
            content: null,
            tool_calls: [
              {
                id: 'call_123',
                type: 'function',
                function: {
                  name: 'get_weather',
                  arguments: '{"location": "London"}',
                },
              },
            ],
          },
        ],
      };

      const context = toPiAiContext(request);

      expect(context.messages).toHaveLength(2);
      const assistantMsg = context.messages[1];
      expect(assistantMsg.role).toBe('assistant');
      expect(Array.isArray(assistantMsg.content)).toBe(true);
    });

    it('should convert tools', () => {
      const request: OpenAIChatRequest = {
        model: 'gpt-4',
        messages: [{ role: 'user', content: 'Hello!' }],
        tools: [
          {
            type: 'function',
            function: {
              name: 'get_weather',
              description: 'Get current weather',
              parameters: {
                type: 'object',
                properties: {
                  location: { type: 'string' },
                },
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

      const response = fromPiAiResponse(piaiMessage, 'req-123', 'gpt-4', 1234567890);

      expect(response.object).toBe('chat.completion');
      expect(response.choices).toHaveLength(1);
      expect(response.choices[0].message.content).toBe('Hello!');
      expect(response.choices[0].finish_reason).toBe('stop');
      expect(response.usage.prompt_tokens).toBe(10);
      expect(response.usage.completion_tokens).toBe(5);
    });

    it('should convert tool call response', () => {
      const piaiMessage = {
        role: 'assistant',
        content: [
          { type: 'text', text: 'Let me check the weather.' },
          {
            type: 'toolCall',
            id: 'call_123',
            name: 'get_weather',
            arguments: { location: 'London' },
          },
        ],
        stopReason: 'toolUse',
        usage: { input: 10, output: 5, cost: { total: 0.0001 } },
      };

      const response = fromPiAiResponse(piaiMessage, 'req-123', 'gpt-4', 1234567890);

      expect(response.choices[0].message.tool_calls).toHaveLength(1);
      expect(response.choices[0].message.tool_calls?.[0]).toEqual({
        id: 'call_123',
        type: 'function',
        function: {
          name: 'get_weather',
          arguments: '{"location":"London"}',
        },
      });
      expect(response.choices[0].finish_reason).toBe('tool_calls');
    });
  });

  describe('streamFromPiAiEvent', () => {
    it('should convert text_delta event', () => {
      const events = Array.from(
        streamFromPiAiEvent(
          { type: 'text_delta', delta: 'Hello', contentIndex: 0 },
          'req-123',
          'gpt-4',
          1234567890
        )
      );

      expect(events).toHaveLength(1);
      expect(events[0].choices[0].delta.content).toBe('Hello');
    });

    it('should convert done event', () => {
      const events = Array.from(
        streamFromPiAiEvent({ type: 'done', reason: 'stop' }, 'req-123', 'gpt-4', 1234567890)
      );

      expect(events).toHaveLength(1);
      expect(events[0].choices[0].finish_reason).toBe('stop');
    });
  });

  describe('OpenAIChatRequestSchema', () => {
    it('should validate valid request', () => {
      const request = {
        model: 'gpt-4',
        messages: [{ role: 'user', content: 'Hello!' }],
        stream: false,
      };

      expect(() => OpenAIChatRequestSchema.parse(request)).not.toThrow();
    });

    it('should reject invalid role', () => {
      const request = {
        model: 'gpt-4',
        messages: [{ role: 'invalid', content: 'Hello!' }],
      };

      expect(() => OpenAIChatRequestSchema.parse(request)).toThrow();
    });

    it('should reject negative temperature', () => {
      const request = {
        model: 'gpt-4',
        messages: [{ role: 'user', content: 'Hello!' }],
        temperature: -1,
      };

      expect(() => OpenAIChatRequestSchema.parse(request)).toThrow();
    });
  });
});
