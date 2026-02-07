# g-copilot-proxy

OpenAI & Anthropic compatible proxy server for GitHub Copilot.

**Now in TypeScript!** - Pure Node.js implementation with direct `@mariozechner/pi-ai` integration. No subprocess overhead.

## Features

- OpenAI-compatible `/v1/chat/completions` endpoint
- Anthropic-compatible `/v1/messages` endpoint
- Full SSE streaming support
- Model aliasing (gpt-4 → claude-sonnet-4.5, etc.)
- GitHub OAuth device flow for authentication
- Docker deployment ready
- **40% less code** than the Python version
- **No subprocess overhead** - direct pi-ai imports

## Quick Start

### Local Development

```bash
# Install dependencies
npm install

# Copy environment file
cp .env.example .env

# Build the project
npm run build

# Start development server (with watch mode)
npm run dev

# Or start the built server
npm start
```

### Docker

```bash
# Build image
docker build -t g-copilot-proxy .

# Run container
docker run -p 8000:8000 \
    -v $(pwd)/data:/app/data \
    -e AUTH_MODE=managed \
    g-copilot-proxy

# Or with docker-compose
docker-compose up
```

## Usage

### OpenAI SDK

```typescript
import OpenAI from 'openai';

const client = new OpenAI({
  baseURL: 'http://localhost:8000/v1',
  apiKey: 'dummy', // Not used - proxy uses OAuth credentials
});

const response = await client.chat.completions.create({
  model: 'claude-sonnet-4.5',
  messages: [{ role: 'user', content: 'Hello!' }],
});

console.log(response.choices[0].message.content);
```

### Anthropic SDK

```typescript
import Anthropic from '@anthropic-ai/sdk';

const client = new Anthropic({
  baseURL: 'http://localhost:8000/v1',
  apiKey: 'dummy', // Not used - proxy uses OAuth credentials
});

const message = await client.messages.create({
  model: 'claude-sonnet-4.5',
  max_tokens: 1024,
  messages: [{ role: 'user', content: 'Hello!' }],
});

console.log(message.content[0].text);
```

### cURL

```bash
# OpenAI format
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "claude-sonnet-4.5",
    "messages": [{"role": "user", "content": "Hello!"}]
  }'

# Anthropic format
curl -X POST http://localhost:8000/v1/messages \
  -H "Content-Type: application/json" \
  -d '{
    "model": "claude-sonnet-4.5",
    "max_tokens": 1024,
    "messages": [{"role": "user", "content": "Hello!"}]
  }'
```

## Available Models

Via GitHub Copilot:

| Model ID | Description |
|----------|-------------|
| `claude-haiku-4.5` | Claude Haiku 4.5 |
| `claude-sonnet-4` | Claude Sonnet 4 |
| `claude-sonnet-4.5` | Claude Sonnet 4.5 |
| `claude-opus-4.5` | Claude Opus 4.5 |
| `gpt-4.1` | GPT 4.1 |
| `gpt-4o` | GPT 4o |
| `gemini-2.5-pro` | Gemini 2.5 Pro |

### Model Aliases

The proxy supports common model aliases that map to GitHub Copilot models:

| Alias | Maps To |
|-------|---------|
| `gpt-4` | claude-sonnet-4.5 |
| `gpt-4o` | claude-sonnet-4.5 |
| `gpt-4o-mini` | claude-haiku-4.5 |
| `gpt-3.5-turbo` | gpt-4.1 |
| `claude-3-opus` | claude-opus-4.5 |
| `claude-3-sonnet` | claude-sonnet-4.5 |
| `claude-3-haiku` | claude-haiku-4.5 |

## Configuration

| Environment Variable | Default | Description |
|---------------------|---------|-------------|
| `PORT` | `8000` | Server port |
| `HOST` | `0.0.0.0` | Server host |
| `AUTH_MODE` | `managed` | Authentication mode: `passthrough` or `managed` |
| `GITHUB_ENTERPRISE_URL` | - | GitHub Enterprise URL (optional) |
| `CORS_ORIGINS` | `*` | CORS allowed origins |
| `LOG_LEVEL` | `info` | Logging level: `debug`, `info`, `warn`, `error` |
| `DATA_DIR` | `./data` | Data directory for auth storage |
| `PIAI_CACHE_RETENTION` | `default` | Cache retention: `default` or `long` |

## Authentication

### Pass-Through Mode

Send your GitHub Copilot token in the Authorization header:

```bash
Authorization: Bearer your-github-copilot-token
```

### Managed Mode

Server handles GitHub OAuth device flow.

**Step 1: Initiate login**
```bash
# Standard GitHub
curl -X POST http://localhost:8000/auth/login

# GitHub Enterprise (optional)
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"enterprise_url": "https://github.yourcompany.com"}'
```

**Step 2: Check server logs for device code**
```
Auth URL: https://github.com/login/device
Instructions: Enter code: XXXX-XXXX
```

**Step 3: Visit the URL and enter the code**

**Step 4: Poll for completion**
```bash
curl http://localhost:8000/auth/status
```

Response when authenticated:
```json
{
  "mode": "managed",
  "authenticated": true,
  "enterprise_url": null
}
```

## Development

```bash
# Run in watch mode (auto-rebuild on changes)
npm run dev

# Run tests
npm test

# Run tests with coverage
npm run test:coverage

# Type check
npm run check

# Format code
npm run format
```

## Project Structure

```
g-copilot-proxy/
├── src/
│   ├── index.ts                 # Entry point
│   ├── config.ts                # Configuration management
│   ├── logger.ts                # Logging utility
│   ├── server.ts                # Hono app setup
│   │
│   ├── api/
│   │   ├── openai/
│   │   │   └── routes.ts        # OpenAI compatible endpoints
│   │   ├── anthropic/
│   │   │   └── routes.ts        # Anthropic compatible endpoints
│   │   └── health.ts            # Health check endpoints
│   │
│   ├── core/
│   │   ├── piai.ts              # Direct pi-ai imports
│   │   ├── mapper-openai.ts     # OpenAI ↔ pi-ai mapping
│   │   └── mapper-anthropic.ts  # Anthropic ↔ pi-ai mapping
│   │
│   └── auth/
│       ├── oauth.ts             # GitHub OAuth manager
│       ├── storage.ts           # Credential storage
│       ├── middleware.ts        # Auth middleware
│       ├── routes.ts            # Auth endpoints
│       └── types.ts             # Auth types
│
├── tests/
│   ├── setup.ts                 # Test setup
│   ├── helpers.ts               # Test utilities
│   ├── config.test.ts
│   ├── mapper-openai.test.ts
│   ├── mapper-anthropic.test.ts
│   ├── auth.test.ts
│   └── api.test.ts
│
├── package.json                 # npm dependencies
├── tsconfig.json                # TypeScript config
├── vitest.config.ts             # Vitest config
├── Dockerfile                   # Docker image
├── docker-compose.yml           # Docker Compose
└── .env.example                 # Environment template
```

## Migration from Python Version

The TypeScript version has several advantages:

| Feature | Python | TypeScript |
|---------|--------|------------|
| **Code Size** | ~3,400 lines | ~2,000 lines (-40%) |
| **pi-ai Integration** | Subprocess spawn | Direct imports |
| **Runtimes** | Python + Node.js | Node.js only |
| **Deployment** | Multi-stage (Python+Node) | Single runtime |
| **Performance** | Subprocess overhead | Direct function calls |
| **Type Safety** | Pydantic runtime | TypeScript compile-time |

The API contracts remain identical - no changes needed for clients!

## Requirements

- **Node.js 20+** - Runtime environment
- **npm** - Package manager

## License

MIT
