/**
 * Config module tests
 */

import { describe, it, expect, beforeEach } from 'vitest';
import { loadConfig, getConfig } from '../src/config.js';

describe('Config', () => {
  beforeEach(() => {
    // Clear environment
    delete process.env.PORT;
    delete process.env.HOST;
    delete process.env.AUTH_MODE;
    delete process.env.CORS_ORIGINS;
    delete process.env.LOG_LEVEL;
    delete process.env.DATA_DIR;
  });

  it('should load config with defaults', () => {
    const config = loadConfig();

    expect(config.PORT).toBe(8000);
    expect(config.HOST).toBe('0.0.0.0');
    expect(config.AUTH_MODE).toBe('managed');
    expect(config.CORS_ORIGINS).toEqual(['*']);
    expect(config.LOG_LEVEL).toBe('info');
    expect(config.DATA_DIR).toBe('./data');
  });

  it('should load config from environment variables', () => {
    process.env.PORT = '9000';
    process.env.HOST = '127.0.0.1';
    process.env.AUTH_MODE = 'passthrough';
    process.env.CORS_ORIGINS = 'https://example.com,https://test.com';
    process.env.LOG_LEVEL = 'debug';
    process.env.DATA_DIR = './custom-data';

    const config = loadConfig();

    expect(config.PORT).toBe(9000);
    expect(config.HOST).toBe('127.0.0.1');
    expect(config.AUTH_MODE).toBe('passthrough');
    expect(config.CORS_ORIGINS).toEqual(['https://example.com', 'https://test.com']);
    expect(config.LOG_LEVEL).toBe('debug');
    expect(config.DATA_DIR).toBe('./custom-data');
  });

  it('should return singleton instance', () => {
    const config1 = getConfig();
    const config2 = getConfig();

    expect(config1).toBe(config2);
  });

  it('should throw on invalid AUTH_MODE', () => {
    process.env.AUTH_MODE = 'invalid' as never;

    expect(() => loadConfig()).toThrow();
  });

  it('should throw on invalid LOG_LEVEL', () => {
    process.env.LOG_LEVEL = 'invalid' as never;

    expect(() => loadConfig()).toThrow();
  });

  it('should parse CORS origins as array when not wildcard', () => {
    process.env.CORS_ORIGINS = 'https://a.com,https://b.com';

    const config = loadConfig();

    expect(config.CORS_ORIGINS).toEqual(['https://a.com', 'https://b.com']);
  });
});
