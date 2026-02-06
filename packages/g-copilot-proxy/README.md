# g-copilot-proxy

OpenAI & Anthropic compatible proxy server for GitHub Copilot.

## Features

- OpenAI-compatible `/v1/chat/completions` endpoint
- Anthropic-compatible `/v1/messages` endpoint
- Full SSE streaming support
- Model aliasing for easy model selection
- Pass-through and managed authentication modes
- Docker deployment ready

## Quick Start

### Local Development

```bash
# Install dependencies
poetry install

# Copy environment file
cp .env.example .env

# Start development server
./scripts/dev.sh

# Or with Poetry
poetry run uvicorn app.main:app --reload
```

### Docker

```bash
# Build image
docker build -t g-copilot-proxy .

# Run container
docker run -p 8000:8000 \
    -v $(pwd)/../ai:/app/ai:ro \
    -e AUTH_MODE=passthrough \
    g-copilot-proxy

# Or with docker-compose
docker-compose up
```

## Usage

### OpenAI SDK

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:8000/v1",
    api_key="your-github-copilot-token"
)

response = client.chat.completions.create(
    model="claude-sonnet-4.5",
    messages=[{"role": "user", "content": "Hello!"}]
)

print(response.choices[0].message.content)
```

### Anthropic SDK

```python
import anthropic

client = anthropic.Anthropic(
    base_url="http://localhost:8000/v1",
    api_key="your-github-copilot-token"
)

message = client.messages.create(
    model="claude-sonnet-4.5",
    max_tokens=1024,
    messages=[{"role": "user", "content": "Hello!"}]
)

print(message.content[0].text)
```

### cURL

```bash
# OpenAI format
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "model": "claude-sonnet-4.5",
    "messages": [{"role": "user", "content": "Hello!"}]
  }'

# Anthropic format
curl -X POST http://localhost:8000/v1/messages \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
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

Run `curl http://localhost:8000/v1/models` for the full list.

## Configuration

| Environment Variable | Default | Description |
|---------------------|---------|-------------|
| `AUTH_MODE` | `passthrough` | Authentication mode: `passthrough` or `managed` |
| `PIAI_MODULE_PATH` | `../ai` | Path to pi-ai Node.js module |
| `CORS_ORIGINS` | `["*"]` | CORS allowed origins |
| `LOG_LEVEL` | `INFO` | Logging level |

## Authentication

### Pass-Through Mode (Default)

Send your GitHub Copilot token in requests:

```bash
Authorization: Bearer your-github-copilot-token
```

### Managed Mode

Server handles OAuth. First, authenticate:

```bash
curl -X POST http://localhost:8000/auth/login
```

Then check status:

```bash
curl http://localhost:8000/auth/status
```

## Testing

```bash
# Run all tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=app

# Run specific test file
poetry run pytest tests/test_openai_api.py
```

## Development

```bash
# Format code
poetry run black app/
poetry run ruff check --fix app/

# Type check
poetry run mypy app/
```

## Project Structure

```
g-copilot-proxy/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI application entry
│   ├── config.py               # Configuration settings
│   ├── api/
│   │   ├── openai/             # OpenAI compatible routes
│   │   └── anthropic/          # Anthropic compatible routes
│   ├── core/
│   │   ├── piai_bridge.py      # Bridge to @mariozechner/pi-ai
│   │   └── mapper.py           # Request/response mapping
│   └── auth/
│       ├── config.py           # Auth configuration
│       ├── github_copilot.py   # GitHub Copilot OAuth
│       ├── middleware.py       # Auth middleware
│       └── routes.py           # Auth endpoints
├── tests/
│   ├── conftest.py
│   ├── test_openai_api.py
│   ├── test_anthropic_api.py
│   └── test_auth.py
├── scripts/
│   └── dev.sh                  # Development server
├── pyproject.toml              # Poetry dependencies
├── Dockerfile
├── docker-compose.yml
└── .env.example
```

## Documentation

- [Implementation Plan](./docs/00-IMPLEMENTATION-PLAN.md)
- [API Reference](./docs/API-REFERENCE.md)
- [Architecture Decisions](./docs/ARCHITECTURE-DECISIONS.md)

## License

MIT
