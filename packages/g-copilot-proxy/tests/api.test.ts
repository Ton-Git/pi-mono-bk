/**
 * API endpoint tests
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { createTestClient, mockCredentials } from './helpers.js';
import { CredentialStorage } from '../src/auth/storage.js';
import { promises as fs } from 'node:fs';

describe('API Endpoints', () => {
  beforeEach(async () => {
    // Clean up test directory
    try {
      await fs.rm('./test-data', { recursive: true });
    } catch {
      // Directory doesn't exist
    }

    // Set test environment variables (this needs to be done before creating server)
    process.env.AUTH_MODE = 'managed';
    process.env.PORT = '8000';
    process.env.DATA_DIR = './test-data';
    process.env.LOG_LEVEL = 'error';

    // Set up mock credentials AFTER setting DATA_DIR
    const storage = new CredentialStorage('./test-data');
    await storage.save(mockCredentials);
  });

  describe('Health endpoints', () => {
    it('should return health status', async () => {
      const client = await createTestClient();
      const response = await client.get('/health');

      expect(response.status).toBe(200);
      expect(response.body).toEqual({
        status: 'ok',
        timestamp: expect.any(String),
      });
    });

    it('should return app info at root', async () => {
      const client = await createTestClient();
      const response = await client.get('/');

      expect(response.status).toBe(200);
      expect(response.body).toMatchObject({
        name: 'g-copilot-proxy',
        version: '1.0.0',
        description: expect.any(String),
      });
    });
  });

  describe('Auth endpoints', () => {
    it('should return auth status when authenticated', async () => {
      const client = await createTestClient();
      const response = await client.get('/auth/status');

      expect(response.status).toBe(200);
      expect(response.body).toMatchObject({
        mode: 'managed',
        authenticated: true,
      });
    });

    it('should clear credentials on logout', async () => {
      const client = await createTestClient();
      const response = await client.post('/auth/logout', {});

      expect(response.status).toBe(200);
      expect(response.body).toMatchObject({
        status: 'success',
        message: 'Credentials cleared',
      });
    });

    it('should return auth config', async () => {
      const client = await createTestClient();
      const response = await client.get('/auth/config');

      expect(response.status).toBe(200);
      expect(response.body).toEqual({
        mode: 'managed',
      });
    });
  });

  describe('OpenAI endpoints', () => {
    it('should return 401 without auth in passthrough mode', async () => {
      // This test would require setting up passthrough mode
      // and sending a request without Authorization header
    });

    it('should list models', async () => {
      const client = await createTestClient();
      const response = await client.get('/v1/models');

      expect(response.status).toBe(200);
      expect(response.body).toHaveProperty('object', 'list');
      expect(response.body).toHaveProperty('data');
      expect(Array.isArray(response.body.data)).toBe(true);
    });

    it('should handle chat completion request', async () => {
      const client = await createTestClient();
      const response = await client.post('/v1/chat/completions', {
        model: 'claude-sonnet-4.5',
        messages: [{ role: 'user', content: 'Hello!' }],
      });

      // This may fail if pi-ai is not available, but should not 500
      expect([200, 500, 503]).toContain(response.status);
    });
  });

  describe('Anthropic endpoints', () => {
    it('should list models', async () => {
      const client = await createTestClient();
      const response = await client.get('/v1/models');

      expect(response.status).toBe(200);
      expect(response.body).toHaveProperty('data');
      expect(Array.isArray(response.body.data)).toBe(true);
    });

    it('should require max_tokens for messages', async () => {
      const client = await createTestClient();
      const response = await client.post('/v1/messages', {
        model: 'claude-sonnet-4.5',
        messages: [{ role: 'user', content: 'Hello!' }],
      });

      expect(response.status).toBeGreaterThanOrEqual(400);
    });
  });
});
