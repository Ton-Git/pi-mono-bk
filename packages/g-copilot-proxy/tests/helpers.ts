/**
 * Test helpers
 */

import { createServer } from '../src/server.js';

/**
 * Create a test client for the Hono app
 */
export async function createTestClient() {
  const app = createServer();

  return {
    async get(path: string) {
      const res = await app.request(path, {
        method: 'GET',
      });
      return {
        status: res.status,
        headers: res.headers,
        body: await res.json(),
      };
    },

    async post(path: string, body: unknown, headers: Record<string, string> = {}) {
      const res = await app.request(path, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...headers,
        },
        body: JSON.stringify(body),
      });
      return {
        status: res.status,
        headers: res.headers,
        body: await res.json(),
      };
    },
  };
}

/**
 * Mock OAuth credentials for testing
 */
export const mockCredentials = {
  accessToken: 'test-access-token',
  refreshToken: 'test-refresh-token',
  expiresAt: Date.now() + 3600000, // 1 hour from now
  createdAt: Date.now(),
};

/**
 * Mock pi-ai stream events
 */
export const mockPiAiEvents = [
  { type: 'start', partial: { model: 'claude-sonnet-4.5' } },
  { type: 'text_start', contentIndex: 0 },
  { type: 'text_delta', delta: 'Hello', contentIndex: 0 },
  { type: 'text_end', content: { text: 'Hello!' }, contentIndex: 0 },
  {
    type: 'done',
    reason: 'stop',
    message: {
      role: 'assistant',
      content: [{ type: 'text', text: 'Hello!' }],
      stopReason: 'stop',
      usage: { input: 10, output: 5, cost: { total: 0.0001 } },
    },
  },
];
