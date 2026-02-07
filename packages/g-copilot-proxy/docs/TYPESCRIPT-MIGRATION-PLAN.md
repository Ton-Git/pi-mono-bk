# TypeScript Migration Plan

## Overview

Rewrite `g-copilot-proxy` from Python (FastAPI) to TypeScript/Node.js, eliminating the subprocess bridge and using `@mariozechner/pi-ai` as a direct dependency.

## Current State Analysis

| Component | Current (Python) | Lines | New (TypeScript) |
|-----------|------------------|-------|------------------|
| Core Application | FastAPI + Pydantic | ~3,400 | Node.js + Zod |
| Tests | pytest | ~1,100 | Vitest |
| pi-ai Integration | subprocess spawn | ~200 | direct import (~50) |
| API Endpoints | FastAPI routes | ~700 | Fastify/Hono routes |
| Docker | Multi-stage | yes | Simplified |

**Key Benefits of Migration:**
- No subprocess overhead (direct `@mariozechner/pi-ai` imports)
- Single runtime (Node.js only)
- Shared types with `pi-ai`
- Simpler deployment
- Better performance

---

## Technology Stack

| Category | Choice | Rationale |
|----------|--------|-----------|
| **Web Framework** | **Hono** | Modern, edge-compatible, excellent TypeScript, smaller than Fastify/Express |
| **Validation** | **Zod** | Already used by pi-ai, great TypeScript inference |
| **Testing** | **Vitest** | Already used in monorepo, fast, Jest-compatible |
| **HTTP Client** | **Native fetch** (Node 18+) | Built-in, no extra dependency |
| **Environment** | **dotenv** | Simple, standard |
| **SSE** | **Custom** (Hono streaming) | Simpler than sse-starlette |

---

## Project Structure

```
g-copilot-proxy/
├── src/
│   ├── index.ts                 # Entry point
│   ├── config.ts                # Configuration & env loading
│   ├── server.ts                # Hono app setup
│   │
│   ├── api/
│   │   ├── openai/
│   │   │   ├── chat.ts          # POST /v1/chat/completions
│   │   │   ├── models.ts        # GET /v1/models
│   │   │   └── schemas.ts       # OpenAI Zod schemas
│   │   │
│   │   ├── anthropic/
│   │   │   ├── messages.ts      # POST /v1/messages
│   │   │   ├── models.ts        # GET /v1/models
│   │   │   └── schemas.ts       # Anthropic Zod schemas
│   │   │
│   │   └── health.ts            # GET /health, GET /
│   │
│   ├── core/
│   │   ├── piai.ts              # Direct pi-ai imports (no subprocess!)
│   │   ├── mapper-openai.ts     # OpenAI ↔ pi-ai mapping
│   │   └── mapper-anthropic.ts  # Anthropic ↔ pi-ai mapping
│   │
│   └── auth/
│       ├── oauth.ts             # GitHub OAuth (pi-ai loginGitHubCopilot)
│       ├── middleware.ts        # Auth middleware
│       ├── routes.ts            # POST /auth/login, GET /auth/status
│       └── storage.ts           # Credential storage (file system)
│
├── tests/
│   ├── setup.ts                 # Test setup
│   ├── api/
│   │   ├── openai.test.ts
│   │   └── anthropic.test.ts
│   ├── auth/
│   │   ├── oauth.test.ts
│   │   └── middleware.test.ts
│   └── core/
│       ├── piai.test.ts
│       └── mapper.test.ts
│
├── package.json
├── tsconfig.json
├── Dockerfile
├── docker-compose.yml
└── README.md
```

---

## Implementation Steps

### Phase 1: Foundation (Est. 2-3 hours)

**1.1 Project Setup**
- [ ] Initialize TypeScript project
- [ ] Install dependencies (Hono, Zod, Vitest, @mariozechner/pi-ai)
- [ ] Configure `tsconfig.json`
- [ ] Create directory structure

**1.2 Configuration**
```typescript
// src/config.ts
import { zodSchema } from './config.schema'

export interface Config {
  server: {
    host: string
    port: number
  }
  auth: {
    mode: 'managed' | 'passthrough'
  }
  cors: {
    origins: string[]
  }
  github: {
    enterpriseUrl?: string
  }
}

export function loadConfig(): Config { ... }
```

**1.3 Server Skeleton**
```typescript
// src/server.ts
import { Hono } from 'hono'
import { cors } from 'hono/cors'

export function createServer(): Hono {
  const app = new Hono()

  // Middleware
  app.use('*', cors())
  app.use('*', logger())

  // Health check
  app.get('/health', (c) => c.json({ status: 'ok' }))

  return app
}
```

---

### Phase 2: Core - pi-ai Bridge (Est. 1-2 hours)

**2.1 Direct Integration (MAJOR SIMPLIFICATION)**

```python
# OLD (Python) - 226 lines with subprocess
class PiaiBridge:
    async def stream_completion(self, ...):
        # Spawn Node.js subprocess
        # Parse stdout line by line
        # Handle SSE parsing
        # Error handling
```

```typescript
// NEW (TypeScript) - ~50 lines, direct imports
import { getModel, stream, type Context } from '@mariozechner/pi-ai'

export async function* streamCompletion(
  model: string,
  context: Context,
  options?: StreamOptions
): AsyncGenerator<SSEEvent> {
  const piaiModel = getModel('github-copilot', model)

  for await (const event of stream(piaiModel, context, options)) {
    // Direct event mapping, no subprocess overhead!
    yield mapToSSE(event)
  }
}
```

**Tasks:**
- [ ] Create `src/core/piai.ts` with direct imports
- [ ] Export `getModel`, `stream`, `complete`
- [ ] Type definitions for stream events

---

### Phase 3: Authentication (Est. 2-3 hours)

**3.1 OAuth Module**
```typescript
// src/auth/oauth.ts
import { loginGitHubCopilot, refreshOAuthToken } from '@mariozechner/pi-ai'

export interface AuthState {
  accessToken: string
  refreshToken: string
  expiresAt: number
  enterpriseUrl?: string
}

export async function initiateLogin(enterpriseUrl?: string): Promise<string> {
  // Returns device code URL
  // Stores state in background
}

export async function refreshCredentials(state: AuthState): Promise<AuthState> {
  // Uses pi-ai's refreshOAuthToken
}
```

**3.2 Storage**
```typescript
// src/auth/storage.ts
import { readFile, writeFile } from 'node:fs/promises'

const AUTH_FILE = './data/auth.json'

export async function saveAuth(state: AuthState): Promise<void>
export async function loadAuth(): Promise<AuthState | null>
export async function clearAuth(): Promise<void>
```

**3.3 Middleware**
```typescript
// src/auth/middleware.ts
export function authMiddleware(config: Config) {
  return async (c: Context, next: Next) => {
    // Check Authorization header or stored credentials
    // Attach to context
    await next()
  }
}
```

**3.4 Routes**
```typescript
// src/auth/routes.ts
app.post('/auth/login', async (c) => {
  const { enterprise_url } = await c.req.json()
  const deviceCode = await initiateLogin(enterprise_url)
  return c.json({ status: 'started', device_code: deviceCode })
})
```

---

### Phase 4: Mappers (Est. 3-4 hours)

**4.1 OpenAI Mapper**
```typescript
// src/core/mapper-openai.ts
import { z } from 'zod'
import type { Context, Tool } from '@mariozechner/pi-ai'

// Schema validation
export const OpenAIChatSchema = z.object({
  model: z.string(),
  messages: z.array(...),
  stream: z.boolean().default(false),
  temperature: z.number().optional(),
  max_tokens: z.number().optional(),
  tools: z.array(...).optional(),
})

// Conversion functions
export function toPiAiContext(req: OpenAIChatRequest): Context
export function fromPiAiResponse(resp: AssistantMessage): OpenAIChatResponse
export function* fromPiAiStream(events: AsyncIterable<Event>): AsyncGenerator<OpenAIChatChunk>
```

**4.2 Anthropic Mapper**
```typescript
// src/core/mapper-anthropic.ts
export const AnthropicMessageSchema = z.object({
  model: z.string(),
  max_tokens: z.number(),
  messages: z.array(...),
  system: z.string().optional(),
  stream: z.boolean().default(false),
  tools: z.array(...).optional(),
})

export function toPiAiContext(req: AnthropicMessageRequest): Context
export function fromPiAiResponse(resp: AssistantMessage): AnthropicMessageResponse
```

---

### Phase 5: API Endpoints (Est. 3-4 hours)

**5.1 OpenAI Endpoints**
```typescript
// src/api/openai/chat.ts
app.post('/v1/chat/completions', authMiddleware, async (c) => {
  const body = OpenAIChatSchema.parse(await c.req.json())

  if (body.stream) {
    // SSE streaming
    return streamText(c, async (stream) => {
      for await (const chunk of streamCompletion(body.model, context)) {
        await stream.write(`data: ${JSON.stringify(chunk)}\n\n`)
      }
    })
  }

  const response = await complete(...)
  return c.json(fromPiAiResponse(response))
})
```

**5.2 Anthropic Endpoints**
```typescript
// src/api/anthropic/messages.ts
app.post('/v1/messages', authMiddleware, async (c) => {
  const body = AnthropicMessageSchema.parse(await c.req.json())
  // Similar to OpenAI but with Anthropic format
})
```

**5.3 Models Endpoints**
```typescript
// src/api/openai/models.ts
app.get('/v1/models', authMiddleware, async (c) => {
  const models = getModels('github-copilot')
  return c.json({
    object: 'list',
    data: models.map(m => ({ id: m.id, ... }))
  })
})
```

---

### Phase 6: Tests (Est. 3-4 hours)

**6.1 Test Setup**
```typescript
// tests/setup.ts
import { beforeEach } from 'vitest'
import { tempWriteDir } from './fixtures'

beforeEach(async () => {
  // Reset auth state
  // Mock pi-ai if needed
})
```

**6.2 Test Files**
```typescript
// tests/api/openai.test.ts
import { describe, it, expect } from 'vitest'
import { createTestClient } from '../helpers'

describe('POST /v1/chat/completions', () => {
  it('should handle non-streaming requests', async () => {
    const client = createTestClient()
    const response = await client.post('/v1/chat/completions', {
      model: 'claude-sonnet-4.5',
      messages: [{ role: 'user', content: 'Hello' }]
    })
    expect(response.status).toBe(200)
  })

  it('should handle streaming requests', async () => {
    // Test SSE streaming
  })
})
```

---

### Phase 7: Docker & Infrastructure (Est. 1-2 hours)

**7.1 Simplified Dockerfile**
```dockerfile
# Only Node.js needed - no Python!
FROM node:20-alpine

WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production

COPY . .
RUN npm run build

EXPOSE 8000
CMD ["node", "dist/index.js"]
```

**7.2 docker-compose.yml**
```yaml
services:
  proxy:
    build: .
    ports:
      - "8000:8000"
    environment:
      - AUTH_MODE=managed
    volumes:
      - ./data:/app/data
```

---

### Phase 8: Documentation (Est. 1 hour)

**8.1 Update README**
- Quick start (npm install + npm run dev)
- Build instructions (npm run build)
- API examples (same endpoints, different runtime)

**8.2 Update API docs**
- Same API contracts (OpenAI/Anthropic compatible)
- No user-facing changes

---

## File-by-File Migration Map

| Python File | TypeScript Equivalent | Est. Lines |
|-------------|----------------------|------------|
| `app/main.py` | `src/index.ts` | ~80 |
| `app/config.py` | `src/config.ts` | ~60 |
| `app/core/piai_bridge.py` | `src/core/piai.ts` | ~50 (was 226) |
| `app/core/mapper.py` | `src/core/mapper-openai.ts` | ~400 |
| | `src/core/mapper-anthropic.ts` | ~250 |
| `app/auth/github_copilot.py` | `src/auth/oauth.ts` | ~80 (was 198) |
| `app/auth/routes.py` | `src/auth/routes.ts` | ~100 |
| `app/auth/middleware.py` | `src/auth/middleware.ts` | ~50 |
| `app/auth/config.py` | Merged into `src/config.ts` | - |
| `app/api/openai/*.py` | `src/api/openai/*.ts` | ~350 |
| `app/api/anthropic/*.py` | `src/api/anthropic/*.ts` | ~400 |

**Total Estimated: ~2,000 lines (vs ~3,400 in Python)**

---

## Dependencies Comparison

### Current (Python)
```
fastapi, uvicorn, pydantic, pydantic-settings
httpx, sse-starlette, python-dotenv, python-multipart
pytest, pytest-asyncio, pytest-cov
+ @mariozechner/pi-ai (Node.js subprocess)
```

### New (TypeScript)
```
hono, zod, dotenv
vitest, @vitest/coverage
+ @mariozechner/pi-ai (direct import)
```

**Much simpler!**

---

## Testing Strategy

### Unit Tests
- Mapper functions (OpenAI/Anthropic ↔ pi-ai)
- Auth state management
- Configuration parsing

### Integration Tests
- Full request/response cycles
- SSE streaming
- OAuth flow (mocked pi-ai)

### Test Doubles
- Mock `@mariozechner/pi-ai` for offline testing
- Fake credential storage

---

## Migration Checklist

### Before Starting
- [ ] Branch: `typescript-migration`
- [ ] Backup current Python version (tag: `v0.1.0-python`)
- [ ] Verify all Python tests pass

### During Migration
- [ ] Keep Python version functional alongside
- [ ] Migrate tests first (TDD approach)
- [ ] Run both versions in parallel for validation

### After Migration
- [ ] All tests pass
- [ ] Docker build works
- [ ] Load testing confirms performance improvement
- [ ] Update all documentation
- [ ] Tag release: `v1.0.0`

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Breaking changes | API contracts remain identical |
| Missing features | Comprehensive test coverage |
| Performance regression | Benchmarks before/after |
| Deployment issues | Docker first, then native |

---

## Success Criteria

1. ✅ All existing tests pass in TypeScript
2. ✅ Same API behavior (OpenAI/Anthropic compatible)
3. ✅ OAuth flow works identically
4. ✅ SSE streaming functional
5. ✅ Docker deployment successful
6. ✅ Performance improved (no subprocess overhead)
7. ✅ Code is simpler and more maintainable

---

## Estimated Timeline

| Phase | Hours | Cumulative |
|-------|-------|------------|
| 1. Foundation | 2-3 | 3 |
| 2. Core - pi-ai Bridge | 1-2 | 5 |
| 3. Authentication | 2-3 | 8 |
| 4. Mappers | 3-4 | 12 |
| 5. API Endpoints | 3-4 | 16 |
| 6. Tests | 3-4 | 20 |
| 7. Docker & Infrastructure | 1-2 | 22 |
| 8. Documentation | 1 | 23 |
| **Buffer** | 2-5 | **25-28 hours** |

**Recommendation:** Plan for 3-4 days of focused development.

---

## Next Steps

Would you like me to:
1. **Start implementation** - Begin with Phase 1 (Foundation)
2. **Create a prototype** - Build a minimal working version first
3. **Refine the plan** - Adjust based on your preferences
4. **Something else** - Different approach or priorities
