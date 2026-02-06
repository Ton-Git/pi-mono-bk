# g-copilot-proxy API Reference

Complete API reference for the g-copilot-proxy server.

## Base URL

```
http://localhost:8000
```

## Authentication

### Pass-Through Mode (Default)

Include your GitHub Copilot token in the `Authorization` header:

```
Authorization: Bearer YOUR_GITHUB_COPILOT_TOKEN
```

### Managed Mode

Use `/auth/login` to authenticate via OAuth, then the server uses stored credentials for all requests.

---

## OpenAI-Compatible Endpoints

### POST /v1/chat/completions

Create a chat completion using OpenAI-compatible format.

**Request Headers:**
| Header | Type | Required | Description |
|--------|------|----------|-------------|
| Authorization | string | Yes* | Bearer token (pass-through mode) |
| Content-Type | string | Yes | application/json |

*Not required in managed mode after OAuth authentication.

**Request Body:**
```json
{
  "model": string,           // Required. Model identifier or alias
  "messages": [              // Required. Array of message objects
    {
      "role": "system|user|assistant|tool",
      "content": string,
      "tool_calls": [        // Optional. For assistant messages with tool calls
        {
          "id": string,
          "type": "function",
          "function": {
            "name": string,
            "parameters": object
          }
        }
      ],
      "tool_call_id": string // Optional. For tool result messages
    }
  ],
  "temperature": number,     // Optional. 0.0 - 2.0
  "max_tokens": integer,     // Optional. Maximum tokens to generate
  "stream": boolean,         // Optional. Enable SSE streaming (default: false)
  "tools": [                 // Optional. Tool definitions
    {
      "type": "function",
      "function": {
        "name": string,
        "description": string,
        "parameters": object  // JSON Schema
      }
    }
  ],
  "tool_choice": string      // Optional. "auto" | "none" | "required"
}
```

**Response (Non-Streaming):**
```json
{
  "id": "chatcmpl-123",
  "object": "chat.completion",
  "created": 1677652288,
  "model": "claude-sonnet-4.5",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": string | null,
        "tool_calls": [
          {
            "id": string,
            "type": "function",
            "function": {
              "name": string,
              "arguments": object
            }
          }
        ]
      },
      "finish_reason": "stop|length|tool_calls"
    }
  ],
  "usage": {
    "prompt_tokens": integer,
    "completion_tokens": integer,
    "total_tokens": integer
  }
}
```

**Response (Streaming):**
Server-Sent Events (SSE) with `data:` prefix:

```
data: {"id":"chatcmpl-123","object":"chat.completion.chunk",...}

data: [DONE]
```

**Example:**
```bash
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "model": "claude-sonnet-4.5",
    "messages": [
      {"role": "system", "content": "You are a helpful assistant."},
      {"role": "user", "content": "What is 2+2?"}
    ]
  }'
```

---

### GET /v1/models

List available models in OpenAI format.

**Response:**
```json
{
  "object": "list",
  "data": [
    {
      "id": "claude-sonnet-4.5",
      "object": "model",
      "created": 1677610600,
      "owned_by": "github-copilot"
    }
  ]
}
```

---

### GET /v1/models/{model_id}

Get details for a specific model.

**Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| model_id | string | Model identifier |

**Response:**
```json
{
  "id": "claude-sonnet-4.5",
  "object": "model",
  "created": 1677610600,
  "owned_by": "github-copilot"
}
```

---

## Anthropic-Compatible Endpoints

### POST /v1/messages

Create a message using Anthropic-compatible format.

**Request Headers:**
| Header | Type | Required | Description |
|--------|------|----------|-------------|
| Authorization | string | Yes* | Bearer token |
| x-api-key | string | Yes* | Alternative to Authorization header |
| Content-Type | string | Yes | application/json |

**Request Body:**
```json
{
  "model": string,           // Required. Model identifier
  "max_tokens": integer,     // Required. Maximum tokens to generate
  "messages": [              // Required. Array of message objects
    {
      "role": "user|assistant",
      "content": string | [
        {
          "type": "text|image|tool_use|tool_result",
          "text": string,
          "id": string,       // For tool_use/tool_result
          "name": string,     // For tool_use
          "input": object,    // For tool_use
          "tool_use_id": string, // For tool_result
          "is_error": boolean, // For tool_result
          "source": {         // For image
            "type": "base64",
            "media_type": "image/png",
            "data": string
          }
        }
      ]
    }
  ],
  "system": string,          // Optional. System prompt
  "tools": [                 // Optional. Tool definitions
    {
      "name": string,
      "description": string,
      "input_schema": object  // JSON Schema
    }
  ],
  "stream": boolean,         // Optional. Enable streaming (default: false)
  "temperature": number      // Optional. Temperature setting
}
```

**Response (Non-Streaming):**
```json
{
  "id": "msg_123",
  "type": "message",
  "role": "assistant",
  "content": [
    {
      "type": "text",
      "text": string
    },
    {
      "type": "tool_use",
      "id": string,
      "name": string,
      "input": object
    }
  ],
  "model": "claude-sonnet-4.5",
  "stop_reason": "end_turn|max_tokens|tool_use|stop_sequence",
  "stop_sequence": null | string,
  "usage": {
    "input_tokens": integer,
    "output_tokens": integer
  }
}
```

**Response (Streaming):**
SSE with event types:

```
event: message_start
data: {"type":"message_start","message":{...}}

event: content_block_start
data: {"type":"content_block_start","index":0,...}

event: content_block_delta
data: {"type":"content_block_delta","index":0,...}

event: content_block_stop
data: {"type":"content_block_stop","index":0}

event: message_delta
data: {"type":"message_delta","delta":{...},"usage":{...}}

event: message_stop
data: {"type":"message_stop"}
```

**Example:**
```bash
curl -X POST http://localhost:8000/v1/messages \
  -H "Content-Type: application/json" \
  -H "x-api-key: YOUR_TOKEN" \
  -d '{
    "model": "claude-opus-4.5",
    "max_tokens": 1024,
    "messages": [
      {"role": "user", "content": "Explain quantum computing"}
    ]
  }'
```

---

### GET /v1/models (Anthropic)

List available models in Anthropic format.

**Response:**
```json
{
  "data": [
    {
      "id": "claude-sonnet-4.5",
      "name": "Claude Sonnet 4.5",
      "display_name": "Claude Sonnet 4.5",
      "type": "model"
    }
  ],
  "has_more": false
}
```

---

## Authentication Endpoints

### GET /auth/config

Get current authentication configuration.

**Response:**
```json
{
  "mode": "passthrough|managed",
  "api_key_header": "Authorization",
  "api_key_prefix": "Bearer"
}
```

---

### GET /auth/status

Get authentication status.

**Response:**
```json
{
  "mode": "passthrough|managed",
  "authenticated": boolean,
  "enterprise_url": string | null
}
```

---

### POST /auth/login

Initiate OAuth login (managed mode only).

**Request Body:**
```json
{
  "enterprise_url": string  // Optional. GitHub Enterprise URL
}
```

**Response:**
```json
{
  "status": "started",
  "message": "OAuth flow initiated. Poll /auth/status to check completion."
}
```

---

### POST /auth/logout

Clear stored credentials (managed mode only).

**Response:**
```json
{
  "status": "success",
  "message": "Credentials cleared"
}
```

---

## Utility Endpoints

### GET /health

Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "version": "0.1.0"
}
```

---

### GET /

Root endpoint with server information.

**Response:**
```json
{
  "name": "g-copilot-proxy",
  "version": "0.1.0",
  "docs": "/docs",
  "openapi": "/openapi.json",
  "authentication": "passthrough|managed"
}
```

---

### GET /docs

Interactive API documentation (Swagger UI).

---

### GET /openapi.json

OpenAPI schema in JSON format.

---

## Model Aliases

The proxy supports common model aliases that map to GitHub Copilot models:

### OpenAI Aliases
| Alias | Maps To |
|-------|---------|
| gpt-4 | gpt-4.1 |
| gpt-4-turbo | gpt-4o |
| gpt-3.5-turbo | gpt-4.1 |

### Claude Aliases
| Alias | Maps To |
|-------|---------|
| claude-3-haiku | claude-haiku-4.5 |
| claude-3-sonnet | claude-sonnet-4 |
| claude-3-opus | claude-opus-4.5 |
| claude-3.5-sonnet | claude-sonnet-4.5 |
| claude | claude-sonnet-4.5 |

---

## Available GitHub Copilot Models

### Claude Models
| Model ID | Description |
|----------|-------------|
| claude-haiku-4.5 | Claude Haiku 4.5 (fast, efficient) |
| claude-sonnet-4 | Claude Sonnet 4 (balanced) |
| claude-sonnet-4.5 | Claude Sonnet 4.5 (balanced, improved) |
| claude-opus-4.5 | Claude Opus 4.5 (highest quality) |
| claude-opus-4.6 | Claude Opus 4.6 (with reasoning) |

### GPT Models
| Model ID | Description |
|----------|-------------|
| gpt-4.1 | GPT 4.1 |
| gpt-4o | GPT 4o (omni-modal) |
| gpt-5 | GPT 5 (with reasoning) |
| gpt-5.1 | GPT 5.1 (with reasoning) |
| gpt-5.2 | GPT 5.2 (with reasoning) |
| gpt-5.3 | GPT 5.3 (with reasoning) |
| gpt-5.1-codex | GPT 5.1 Codex (code-focused) |

### Gemini Models
| Model ID | Description |
|----------|-------------|
| gemini-2.5-pro | Gemini 2.5 Pro |
| gemini-3-flash-preview | Gemini 3 Flash Preview |
| gemini-3-pro-preview | Gemini 3 Pro Preview |

### Grok Models
| Model ID | Description |
|----------|-------------|
| grok-code-fast-1 | Grok Code Fast 1 |

---

## Error Responses

Errors are returned with appropriate HTTP status codes:

```json
{
  "detail": "Error message description"
}
```

### Common HTTP Status Codes

| Status | Description |
|--------|-------------|
| 200 | Success |
| 400 | Bad Request (invalid parameters) |
| 401 | Unauthorized (missing/invalid credentials) |
| 422 | Unprocessable Entity (validation error) |
| 500 | Internal Server Error |

---

## Streaming Response Format

### OpenAI Streaming

OpenAI uses a simple SSE format with `data:` prefix:

```
data: {"id":"chatcmpl-123","choices":[{...}]}

data: [DONE]
```

### Anthropic Streaming

Anthropic uses typed SSE events:

```
event: message_start
data: {"type":"message_start",...}

event: content_block_delta
data: {"type":"content_block_delta",...}

event: message_stop
data: {"type":"message_stop"}
```

Both formats are fully supported by the proxy.

---

## Rate Limiting

Rate limiting is configured via environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| RATE_LIMIT_REQUESTS | 100 | Requests per period |
| RATE_LIMIT_PERIOD | 60 | Period in seconds |

---

## CORS Configuration

CORS is configured via environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| CORS_ORIGINS | ["*"] | Allowed origins |
| CORS_ALLOW_CREDENTIALS | true | Allow credentials |
| CORS_ALLOW_METHODS | ["*"] | Allowed methods |
| CORS_ALLOW_HEADERS | ["*"] | Allowed headers |

**Important:** Restrict `CORS_ORIGINS` in production for security.

---

## SDK Usage Examples

### OpenAI Python SDK

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:8000/v1",
    api_key="your-github-copilot-token"
)

response = client.chat.completions.create(
    model="claude-sonnet-4.5",
    messages=[
        {"role": "user", "content": "Hello!"}
    ]
)

print(response.choices[0].message.content)
```

### Anthropic Python SDK

```python
import anthropic

client = anthropic.Anthropic(
    base_url="http://localhost:8000/v1",
    api_key="your-github-copilot-token"
)

message = client.messages.create(
    model="claude-opus-4.5",
    max_tokens=1024,
    messages=[
        {"role": "user", "content": "Hello!"}
    ]
)

print(message.content[0].text)
```

### JavaScript (OpenAI SDK)

```javascript
import OpenAI from 'openai';

const client = new OpenAI({
  baseURL: 'http://localhost:8000/v1',
  apiKey: 'your-github-copilot-token'
});

const response = await client.chat.completions.create({
  model: 'claude-sonnet-4.5',
  messages: [{ role: 'user', content: 'Hello!' }]
});

console.log(response.choices[0].message.content);
```

---

## Webhook Support (Future)

Future versions may support webhooks for asynchronous responses:

```json
POST /v1/chat/completions
{
  "model": "claude-sonnet-4.5",
  "messages": [...],
  "webhook": {
    "url": "https://your-server.com/callback",
    "secret": "webhook-secret"
  }
}
```

---

For more implementation details, see the [Implementation Plan](./00-IMPLEMENTATION-PLAN.md).
