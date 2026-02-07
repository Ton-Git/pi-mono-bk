/**
 * Authentication module tests
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { CredentialStorage } from '../src/auth/storage.js';
import { createAuthMiddleware } from '../src/auth/middleware.js';
import type { OAuthCredentials } from '../src/auth/types.js';
import type { Config } from '../src/config.js';
import { promises as fs } from 'node:fs';

describe('CredentialStorage', () => {
  const testDataDir = './test-auth-data';
  let storage: CredentialStorage;

  beforeEach(async () => {
    // Clean up test directory
    try {
      await fs.rm(testDataDir, { recursive: true });
    } catch {
      // Directory doesn't exist
    }
    storage = new CredentialStorage(testDataDir);
  });

  it('should save and load credentials', async () => {
    const credentials: OAuthCredentials = {
      accessToken: 'test-token',
      refreshToken: 'test-refresh',
      expiresAt: Date.now() + 3600000,
      createdAt: Date.now(),
    };

    await storage.save(credentials);
    const loaded = await storage.load();

    expect(loaded).toEqual(credentials);
  });

  it('should return null when no credentials exist', async () => {
    const loaded = await storage.load();
    expect(loaded).toBeNull();
  });

  it('should check if credentials exist', async () => {
    expect(await storage.exists()).toBe(false);

    const credentials: OAuthCredentials = {
      accessToken: 'test-token',
      refreshToken: 'test-refresh',
      expiresAt: Date.now() + 3600000,
      createdAt: Date.now(),
    };

    await storage.save(credentials);
    expect(await storage.exists()).toBe(true);
  });

  it('should clear credentials', async () => {
    const credentials: OAuthCredentials = {
      accessToken: 'test-token',
      refreshToken: 'test-refresh',
      expiresAt: Date.now() + 3600000,
      createdAt: Date.now(),
    };

    await storage.save(credentials);
    expect(await storage.exists()).toBe(true);

    await storage.clear();
    expect(await storage.exists()).toBe(false);
  });

  it('should detect expired credentials', async () => {
    const credentials: OAuthCredentials = {
      accessToken: 'test-token',
      refreshToken: 'test-refresh',
      expiresAt: Date.now() - 1000, // Expired 1 second ago
      createdAt: Date.now() - 3600000,
    };

    await storage.save(credentials);
    expect(await storage.isExpired()).toBe(true);
  });

  it('should detect credentials near expiration with buffer', async () => {
    const credentials: OAuthCredentials = {
      accessToken: 'test-token',
      refreshToken: 'test-refresh',
      expiresAt: Date.now() + 4 * 60 * 1000, // Expires in 4 minutes (less than 5 min buffer)
      createdAt: Date.now(),
    };

    await storage.save(credentials);
    expect(await storage.isExpired()).toBe(true);
  });
});

describe('Auth Middleware', () => {
  const mockConfig: Config = {
    PORT: 8000,
    HOST: '0.0.0.0',
    AUTH_MODE: 'managed',
    CORS_ORIGINS: ['*'],
    LOG_LEVEL: 'info',
    DATA_DIR: './test-data',
    PIAI_CACHE_RETENTION: 'default',
    GITHUB_ENTERPRISE_URL: undefined,
  };

  beforeEach(async () => {
    // Clean up test directory
    try {
      await fs.rm('./test-data', { recursive: true });
    } catch {
      // Directory doesn't exist
    }
  });

  it('should pass with valid credentials in managed mode', async () => {
    const storage = new CredentialStorage('./test-data');
    const credentials: OAuthCredentials = {
      accessToken: 'test-token',
      refreshToken: 'test-refresh',
      expiresAt: Date.now() + 3600000,
      createdAt: Date.now(),
    };
    await storage.save(credentials);

    const middleware = createAuthMiddleware(mockConfig);
    const mockContext = {
      req: { header: vi.fn() },
      set: vi.fn(),
      json: vi.fn(),
    };
    const mockNext = vi.fn();

    await middleware(mockContext as any, mockNext);

    expect(mockContext.set).toHaveBeenCalledWith(
      'auth',
      expect.objectContaining({
        accessToken: 'test-token',
        source: 'managed',
      })
    );
    expect(mockNext).toHaveBeenCalled();
  });

  it('should reject without credentials in managed mode', async () => {
    const middleware = createAuthMiddleware(mockConfig);
    const mockContext = {
      req: { header: vi.fn() },
      set: vi.fn(),
      json: vi.fn((data: any, status: number) => ({ data, status })),
    };
    const mockNext = vi.fn();

    await middleware(mockContext as any, mockNext);

    expect(mockContext.json).toHaveBeenCalledWith(
      expect.objectContaining({
        error: expect.stringContaining('No OAuth credentials'),
      }),
      401
    );
    expect(mockNext).not.toHaveBeenCalled();
  });

  it('should accept Bearer token in passthrough mode', async () => {
    const config = { ...mockConfig, AUTH_MODE: 'passthrough' as const };
    const middleware = createAuthMiddleware(config);
    const mockContext = {
      req: { header: vi.fn((name: string) => (name === 'Authorization' ? 'Bearer test-token' : null)) },
      set: vi.fn(),
      json: vi.fn(),
    };
    const mockNext = vi.fn();

    await middleware(mockContext as any, mockNext);

    expect(mockContext.set).toHaveBeenCalledWith('auth', {
      accessToken: 'test-token',
      source: 'bearer',
    });
    expect(mockNext).toHaveBeenCalled();
  });
});
