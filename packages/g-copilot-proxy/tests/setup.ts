/**
 * Test setup and configuration
 */

// Set test environment BEFORE importing any modules
process.env.NODE_ENV = 'test';

import { beforeEach, afterEach } from 'vitest';
import { resetConfig } from '../src/config.js';
import { resetLogger } from '../src/logger.js';
import { resetOAuthManager } from '../src/auth/oauth.js';
import { resetBridge } from '../src/core/piai.js';

// Reset all singletons before each test
beforeEach(() => {
  // Clear environment
  delete process.env.AUTH_MODE;
  delete process.env.PORT;
  delete process.env.DATA_DIR;
  delete process.env.LOG_LEVEL;

  // Now reset singletons and set test environment
  resetConfig();
  resetLogger();
  resetOAuthManager();
  resetBridge();

  // Set test environment variables (these override .env file)
  process.env.AUTH_MODE = 'managed';
  process.env.PORT = '8000';
  process.env.DATA_DIR = './test-data';
  process.env.LOG_LEVEL = 'error'; // Reduce log noise in tests (must be lowercase)
});

// Cleanup after each test
afterEach(() => {
  // Reset environment
  delete process.env.AUTH_MODE;
  delete process.env.PORT;
  delete process.env.DATA_DIR;
  delete process.env.LOG_LEVEL;
});
