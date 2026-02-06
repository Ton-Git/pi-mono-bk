# g-copilot-proxy User Guide

This guide will help you get started with `g-copilot-proxy` - an OpenAI & Anthropic compatible proxy server for GitHub Copilot.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Quick Start](#quick-start)
3. [Installation](#installation)
4. [Configuration](#configuration)
5. [Running the Server](#running-the-server)
6. [Testing the API](#testing-the-api)
7. [Usage Examples](#usage-examples)
8. [Docker Deployment](#docker-deployment)
9. [Troubleshooting](#troubleshooting)
10. [FAQ](#faq)

---

## Prerequisites

Before you begin, ensure you have the following installed:

- **Python 3.11 or higher** - [Download here](https://www.python.org/downloads/)
- **Node.js 18 or higher** - [Download here](https://nodejs.org/)
- **Poetry** (Python dependency manager) - Install via:
  ```bash
  curl -sSL https://install.python-poetry.org | python3 -
  ```
- **Docker** (optional, for containerized deployment) - [Download here](https://www.docker.com/)

### Verifying Prerequisites

```bash
# Check Python version
python --version  # Should be 3.11+

# Check Node.js version
node --version     # Should be 18+

# Check Poetry installation
poetry --version
```

---

## Quick Start

Get the server running in under 5 minutes:

```bash
# 1. Navigate to the project directory
cd packages/g-copilot-proxy

# 2. Install dependencies
poetry install

# 3. Create environment file
cp .env.example .env

# 4. Start the server
poetry run uvicorn app.main:app --reload

# 5. Visit the API documentation
# Open http://localhost:8000/docs in your browser
```

That's it! Your server is now running.

---

## Installation

### Step 1: Navigate to the Project

```bash
cd /workspaces/pi-mono-bk/packages/g-copilot-proxy
```

### Step 2: Install Python Dependencies

Using Poetry (recommended):

```bash
poetry install
```

Or using pip:

```bash
pip install fastapi uvicorn pydantic pydantic-settings httpx python-multipart sse-starlette python-dotenv
```

### Step 3: Create Environment Configuration

Copy the example environment file:

```bash
cp .env.example .env
```

Edit `.env` to customize your settings (see [Configuration](#configuration)).

### Step 4: Verify pi-ai Module Path

The proxy requires access to the `@mariozechner/pi-ai` Node.js module. By default, it looks for it at `../ai` relative to the proxy directory.

If your pi-ai module is elsewhere, update `PIAI_MODULE_PATH` in your `.env` file.

---

## Configuration

The server is configured via environment variables. Create a `.env` file from the example:

```bash
cp .env.example .env
```

### Configuration Options

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_NAME` | `g-copilot-proxy` | Application name |
| `HOST` | `0.0.0.0` | Server host |
| `PORT` | `8000` | Server port |
| `DEBUG` | `false` | Enable debug mode |
| `AUTH_MODE` | `passthrough` | Auth mode: `passthrough` or `managed` |
| `PIAI_MODULE_PATH` | `../ai` | Path to pi-ai Node.js module |
| `PIAI_NODE_PATH` | `node` | Path to Node.js executable |
| `CORS_ORIGINS` | `["*"]` | CORS allowed origins |
| `LOG_LEVEL` | `INFO` | Logging level |

### Example `.env` File

```bash
# Server Configuration
APP_NAME=g-copilot-proxy
HOST=0.0.0.0
PORT=8000
DEBUG=false

# pi-ai Bridge
PIAI_MODULE_PATH=../ai
PIAI_NODE_PATH=node

# Authentication
AUTH_MODE=passthrough

# CORS
CORS_ORIGINS=["*"]

# Logging
LOG_LEVEL=INFO
```

---

## Running the Server

### Development Mode

#### Option 1: Using Poetry (Recommended)

```bash
poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### Option 2: Using the Dev Script

```bash
./scripts/dev.sh
```

#### Option 3: Using pip-installed uvicorn

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**What to expect:**

```
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### Production Mode

For production, run without `--reload`:

```bash
poetry run uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Accessing Interactive Documentation

Once the server is running, visit:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI Schema**: http://localhost:8000/openapi.json

---

## Testing the API

### Health Check

Verify the server is running:

```bash
curl http://localhost:8000/health
```

**Response:**
```json
{
  "status": "healthy",
  "version": "0.1.0"
}
```

### List Available Models

```bash
curl http://localhost:8000/v1/models
```

### Test OpenAI-Compatible Endpoint

```bash
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_GITHUB_COPILOT_TOKEN" \
  -d '{
    "model": "claude-sonnet-4.5",
    "messages": [{"role": "user", "content": "Say hello!"}]
  }'
```

### Test Anthropic-Compatible Endpoint

```bash
curl -X POST http://localhost:8000/v1/messages \
  -H "Content-Type: application/json" \
  -H "x-api-key: YOUR_GITHUB_COPILOT_TOKEN" \
  -d '{
    "model": "claude-sonnet-4.5",
    "max_tokens": 1024,
    "messages": [{"role": "user", "content": "Say hello!"}]
  }'
```

---

## Usage Examples

### Using with OpenAI Python SDK

```python
from openai import OpenAI

# Initialize client pointing to your proxy
client = OpenAI(
    base_url="http://localhost:8000/v1",
    api_key="your-github-copilot-token"  # Your GitHub Copilot token
)

# Create a chat completion
response = client.chat.completions.create(
    model="claude-sonnet-4.5",
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Explain quantum computing in simple terms."}
    ],
    max_tokens=500
)

print(response.choices[0].message.content)
```

### Using with Anthropic Python SDK

```python
import anthropic

# Initialize client pointing to your proxy
client = anthropic.Anthropic(
    base_url="http://localhost:8000/v1",
    api_key="your-github-copilot-token"  # Your GitHub Copilot token
)

# Create a message
message = client.messages.create(
    model="claude-opus-4.5",
    max_tokens=1024,
    system="You are a helpful assistant.",
    messages=[
        {"role": "user", "content": "Explain quantum computing in simple terms."}
    ]
)

print(message.content[0].text)
```

### Using with cURL (Streaming)

```bash
# OpenAI streaming
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "model": "claude-sonnet-4.5",
    "messages": [{"role": "user", "content": "Count to 10"}],
    "stream": true
  }'

# Anthropic streaming
curl -X POST http://localhost:8000/v1/messages \
  -H "Content-Type: application/json" \
  -H "x-api-key: YOUR_TOKEN" \
  -d '{
    "model": "claude-sonnet-4.5",
    "max_tokens": 100,
    "messages": [{"role": "user", "content": "Count to 10"}],
    "stream": true
  }'
```

### Using with JavaScript/TypeScript

```javascript
import OpenAI from 'openai';

const client = new OpenAI({
  baseURL: 'http://localhost:8000/v1',
  apiKey: 'your-github-copilot-token'
});

async function main() {
  const response = await client.chat.completions.create({
    model: 'claude-sonnet-4.5',
    messages: [{ role: 'user', content: 'Hello!' }],
  });

  console.log(response.choices[0].message.content);
}

main();
```

---

## Docker Deployment

### Building the Docker Image

```bash
cd packages/g-copilot-proxy
docker build -t g-copilot-proxy .
```

### Running with Docker

```bash
docker run -d \
  --name g-copilot-proxy \
  -p 8000:8000 \
  -v $(pwd)/../ai:/app/ai:ro \
  -e AUTH_MODE=passthrough \
  -e LOG_LEVEL=INFO \
  g-copilot-proxy
```

### Running with Docker Compose

```bash
cd packages/g-copilot-proxy
docker-compose up -d
```

### Docker Environment Variables

You can pass environment variables to Docker:

```bash
docker run -d \
  --name g-copilot-proxy \
  -p 8000:8000 \
  -e AUTH_MODE=passthrough \
  -e CORS_ORIGINS='["https://yourdomain.com"]' \
  -e LOG_LEVEL=INFO \
  g-copilot-proxy
```

---

## Authentication

The proxy supports two authentication modes:

### Pass-Through Mode (Default)

In pass-through mode, clients send their GitHub Copilot token directly with each request.

**Setup:**
```bash
# In .env
AUTH_MODE=passthrough
```

**Usage:**
```bash
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Authorization: Bearer YOUR_GITHUB_COPILOT_TOKEN" \
  -d '{"model": "claude-sonnet-4.5", "messages": [...]}'
```

### Managed Mode

In managed mode, the server handles OAuth and stores credentials for all requests.

**Setup:**
```bash
# In .env
AUTH_MODE=managed
```

**Usage:**

1. Initiate OAuth:
```bash
curl -X POST http://localhost:8000/auth/login
```

2. Check authentication status:
```bash
curl http://localhost:8000/auth/status
```

3. Make requests (no token needed):
```bash
curl -X POST http://localhost:8000/v1/chat/completions \
  -d '{"model": "claude-sonnet-4.5", "messages": [...]}'
```

4. Logout (optional):
```bash
curl -X POST http://localhost:8000/auth/logout
```

---

## Model Aliases

The proxy supports common model aliases:

| Alias | Actual Model |
|-------|--------------|
| `gpt-4` | `gpt-4.1` |
| `claude-3.5-sonnet` | `claude-sonnet-4.5` |
| `claude` | `claude-sonnet-4.5` (default) |

You can use these aliases in your requests:

```python
# All of these work the same
client.chat.completions.create(model="claude", ...)
client.chat.completions.create(model="claude-3.5-sonnet", ...)
client.chat.completions.create(model="claude-sonnet-4.5", ...)
```

---

## Troubleshooting

### Server Won't Start

**Issue:** `ModuleNotFoundError: No module named 'app'`

**Solution:** Make sure you're in the correct directory and dependencies are installed:
```bash
cd packages/g-copilot-proxy
poetry install
```

### Issue: "pi-ai module not found"

**Solution:** Update the `PIAI_MODULE_PATH` in your `.env` file to point to the correct location of the pi-ai Node.js module.

### Issue: "Node.js command failed"

**Solution:** Ensure Node.js is installed and accessible:
```bash
node --version
```

Update `PIAI_NODE_PATH` if node is not in your PATH.

### Authentication Errors

**Issue:** `401 Unauthorized`

**Solution:**
- Verify your GitHub Copilot token is valid
- Check that `Authorization` header is formatted correctly: `Bearer <token>`
- If using managed mode, ensure you've completed the OAuth flow

### CORS Errors

**Issue:** Browser shows CORS error

**Solution:** Update `CORS_ORIGINS` in `.env`:
```bash
CORS_ORIGINS=["https://yourdomain.com"]
```

---

## FAQ

### What is g-copilot-proxy?

It's a proxy server that exposes OpenAI and Anthropic compatible endpoints, backed by GitHub Copilot. This allows you to use existing AI SDKs with your GitHub Copilot subscription.

### Do I need a GitHub Copilot subscription?

Yes, you need a valid GitHub Copilot subscription. The proxy forwards requests to GitHub Copilot's API.

### Which models are available?

The proxy exposes all models available through GitHub Copilot, including Claude (Sonnet, Opus, Haiku), GPT (4.1, 4o, 5), Gemini, and more. Run `curl http://localhost:8000/v1/models` for the full list.

### Can I use this in production?

Yes! The proxy includes Docker support, health checks, and is designed for production use. See the [Docker Deployment](#docker-deployment) section.

### Is my API key stored?

- **Pass-through mode:** No, your token is forwarded directly to GitHub Copilot
- **Managed mode:** Yes, OAuth credentials are stored in `.copilot-auth.json`

### Can I host this publicly?

Yes, but you should:
1. Set `AUTH_MODE=managed` to avoid exposing individual tokens
2. Restrict `CORS_ORIGINS` to your domain
3. Use HTTPS (via nginx or a load balancer)
4. Implement rate limiting

### How do I get a GitHub Copilot token?

You can obtain your GitHub Copilot token through:
- GitHub Settings → Developer Settings → Personal Access Tokens
- Or by using the proxy's built-in OAuth flow in managed mode

---

## Getting Help

- **Documentation**: See the `docs/` directory for detailed technical docs
- **API Reference**: `docs/API-REFERENCE.md`
- **Architecture Decisions**: `docs/ARCHITECTURE-DECISIONS.md`
- **Issues**: Report bugs or request features via the project's issue tracker

---

## Next Steps

1. Explore the [API Reference](./API-REFERENCE.md) for detailed endpoint documentation
2. Read the [Implementation Plan](./00-IMPLEMENTATION-PLAN.md) to understand how it works
3. Check out the [Architecture Decisions](./ARCHITECTURE-DECISIONS.md) for design rationale
4. Run the test suite: `poetry run pytest`

Happy building! 🚀
