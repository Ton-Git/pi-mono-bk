# g-copilot-proxy Postman Collection

API requests for testing the g-copilot-proxy server running on `localhost:8000`.

## Base URL
```
http://localhost:8000
```

## Authentication
The proxy uses GitHub Device OAuth flow for authentication.

**Before testing API endpoints:**
1. Visit `http://localhost:8000/auth/login` to initiate OAuth flow
2. Complete the GitHub device authorization
3. Credentials are stored and managed automatically by the server

No `Authorization` headers are needed in API requests.

---

## Health Check Endpoints

### 1. Root Endpoint
```
GET http://localhost:8000/
```

**Response:**
```json
{
  "name": "g-copilot-proxy",
  "version": "1.0.0",
  "description": "OpenAI & Anthropic compatible proxy server for GitHub Copilot",
  "auth_mode": "managed"
}
```

### 2. Health Check
```
GET http://localhost:8000/health
```

**Response:**
```json
{
  "status": "ok",
  "timestamp": "2026-02-07T12:00:00.000Z"
}
```

---

## OpenAI-Compatible Endpoints

### 3. List Models (OpenAI)
```
GET http://localhost:8000/v1/models
```

**Response:**
```json
{
  "object": "list",
  "data": [
    {
      "id": "claude-opus-4.5",
      "object": "model",
      "created": 1234567890,
      "owned_by": "github-copilot"
    }
  ]
}
```

### 4. Chat Completion (OpenAI) - Non-Streaming
```
POST http://localhost:8000/v1/chat/completions
Content-Type: application/json
```

**Request Body:**
```json
{
  "model": "gpt-5-mini",
  "messages": [
    {
      "role": "system",
      "content": "You are a helpful assistant."
    },
    {
      "role": "user",
      "content": "Hello! Can you explain what TypeScript is?"
    }
  ],
  "stream": false,
  "temperature": 0.7,
  "max_tokens": 500
}
```

**Response:**
```json
{
  "id": "chatcmpl-abc123",
  "object": "chat.completion",
  "created": 1234567890,
  "model": "gpt-5-mini",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "TypeScript is a strongly typed programming language..."
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 20,
    "completion_tokens": 50,
    "total_tokens": 70
  }
}
```

### 5. Chat Completion (OpenAI) - Streaming
```
POST http://localhost:8000/v1/chat/completions
Content-Type: application/json
```

**Request Body:**
```json
{
  "model": "gpt-5-mini",
  "messages": [
    {
      "role": "user",
      "content": "Write a short haiku about coding"
    }
  ],
  "stream": true,
  "temperature": 0.8,
  "max_tokens": 100
}
```

**Streaming Response (SSE):**
```
data: {"id":"chatcmpl-abc123","object":"chat.completion.chunk","created":1234567890,"model":"gpt-5-mini","choices":[{"index":0,"delta":{"role":"assistant"},"finish_reason":null}]}

data: {"id":"chatcmpl-abc123","object":"chat.completion.chunk","created":1234567890,"model":"gpt-5-mini","choices":[{"index":0,"delta":{"content":"Code"},"finish_reason":null}]}

data: [DONE]
```

### 6. Chat Completion with Tools (OpenAI)
```
POST http://localhost:8000/v1/chat/completions
Content-Type: application/json
```

**Request Body:**
```json
{
  "model": "gpt-5-mini",
  "messages": [
    {
      "role": "user",
      "content": "What's the weather in San Francisco?"
    }
  ],
  "tools": [
    {
      "type": "function",
      "function": {
        "name": "get_weather",
        "description": "Get the current weather for a location",
        "parameters": {
          "type": "object",
          "properties": {
            "location": {
              "type": "string",
              "description": "The city and state, e.g. San Francisco, CA"
            }
          },
          "required": ["location"]
        }
      }
    }
  ],
  "tool_choice": "auto",
  "stream": false
}
```

### 7. Chat Completion with Image (OpenAI)
```
POST http://localhost:8000/v1/chat/completions
Content-Type: application/json
```

**Request Body:**
```json
{
  "model": "gpt-5-mini",
  "messages": [
    {
      "role": "user",
      "content": [
        {
          "type": "text",
          "text": "Describe this image"
        },
        {
          "type": "image_url",
          "image_url": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        }
      ]
    }
  ],
  "stream": false
}
```

---

## Anthropic-Compatible Endpoints

### 8. List Models (Anthropic)
```
GET http://localhost:8000/v1/models
```

**Response:**
```json
{
  "data": [
    {
      "id": "claude-opus-4.5",
      "name": "Claude Opus 4.5",
      "description": "Most powerful model for complex tasks",
      "context_window": 200000,
      "type": "model"
    }
  ]
}
```

### 9. Message (Anthropic) - Non-Streaming
```
POST http://localhost:8000/v1/messages
Content-Type: application/json
```

**Anthropic-Version: 2023-06-01**

**Request Body:**
```json
{
  "model": "claude-3-5-sonnet-20241022",
  "max_tokens": 500,
  "messages": [
    {
      "role": "user",
      "content": "Hello! Can you explain what REST APIs are?"
    }
  ],
  "system": "You are a helpful technical assistant.",
  "temperature": 0.7
}
```

**Response:**
```json
{
  "id": "msg_abc123",
  "type": "message",
  "role": "assistant",
  "content": [
    {
      "type": "text",
      "text": "REST (Representational State Transfer) APIs are..."
    }
  ],
  "model": "claude-3-5-sonnet-20241022",
  "stop_reason": "end_turn",
  "usage": {
    "input_tokens": 25,
    "output_tokens": 100
  }
}
```

### 10. Message (Anthropic) - Streaming
```
POST http://localhost:8000/v1/messages
Content-Type: application/json
```

**Anthropic-Version: 2023-06-01**

**Request Body:**
```json
{
  "model": "claude-3-5-sonnet-20241022",
  "max_tokens": 100,
  "messages": [
    {
      "role": "user",
      "content": "Count from 1 to 5"
    }
  ],
  "stream": true
}
```

**Streaming Response (SSE):**
```
event: message_start
data: {"id":"msg_abc123","type":"message","role":"assistant","content":[],"model":"claude-3-5-sonnet-20241022","stop_reason":null,"usage":{"input_tokens":10,"output_tokens":0}}

event: content_block_delta
data: {"type":"content_block_delta","index":0,"delta":{"type":"text_delta","text":"1"}}

event: message_stop
data: {"type":"message_stop","stop_reason":"end_turn"}
```

### 11. Message with Tools (Anthropic)
```
POST http://localhost:8000/v1/messages
Content-Type: application/json
```

**Anthropic-Version: 2023-06-01**

**Request Body:**
```json
{
  "model": "claude-3-5-sonnet-20241022",
  "max_tokens": 500,
  "messages": [
    {
      "role": "user",
      "content": "What time is it in New York?"
    }
  ],
  "tools": [
    {
      "name": "get_time",
      "description": "Get the current time for a timezone",
      "input_schema": {
        "type": "object",
        "properties": {
          "timezone": {
            "type": "string",
            "description": "IANA timezone, e.g. America/New_York"
          }
        },
        "required": ["timezone"]
      }
    }
  ]
}
```

### 12. Message with Image (Anthropic)
```
POST http://localhost:8000/v1/messages
Content-Type: application/json
```

**Anthropic-Version: 2023-06-01**

**Request Body:**
```json
{
  "model": "claude-3-5-sonnet-20241022",
  "max_tokens": 300,
  "messages": [
    {
      "role": "user",
      "content": [
        {
          "type": "text",
          "text": "What do you see in this image?"
        },
        {
          "type": "image",
          "source": {
            "type": "base64",
            "media_type": "image/png",
            "data": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
          }
        }
      ]
    }
  ]
}
```

---

## Authentication Endpoints

### 13. Login (Managed Mode)
```
GET http://localhost:8000/auth/login
```

**Response:** Redirects to GitHub OAuth login page

### 14. Callback
```
GET http://localhost:8000/auth/callback?code=<oauth-code>
```

**Response:** OAuth credentials stored and ready to use

### 15. Logout
```
POST http://localhost:8000/auth/logout
```

**Response:**
```json
{
  "success": true
}
```

---

## Model Aliases

The proxy automatically maps common model names to GitHub Copilot models:

| Requested Model | Mapped To |
|-----------------|-----------|
| `gpt-4` | `claude-sonnet-4.5` |
| `gpt-4-turbo` | `claude-sonnet-4.5` |
| `gpt-4o` | `claude-sonnet-4.5` |
| `gpt-4o-mini` | `claude-haiku-4.5` |
| `gpt-3.5-turbo` | `gpt-4.1` |
| `claude-3-opus` | `claude-opus-4.5` |
| `claude-3-sonnet` | `claude-sonnet-4.5` |
| `claude-3-haiku` | `claude-haiku-4.5` |

**Note:** `gpt-5-mini` (as requested) will be passed through as-is since it's not in the alias table.
