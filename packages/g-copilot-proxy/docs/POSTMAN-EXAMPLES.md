# g-copilot-proxy API Examples

Ready-to-use examples for Postman or curl. Replace `YOUR_GITHUB_COPILOT_TOKEN` with your actual token.

## Base URL

```
http://localhost:8000
```

---

## OpenAI-Compatible Endpoints

### 1. List Models

**Endpoint:** `GET /v1/models`

**cURL:**
```bash
curl -X GET http://localhost:8000/v1/models
```

**Postman:**
- Method: `GET`
- URL: `http://localhost:8000/v1/models`
- Headers: (none required)

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

### 2. Chat Completion (Non-Streaming)

**Endpoint:** `POST /v1/chat/completions`

**cURL:**
```bash
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_GITHUB_COPILOT_TOKEN" \
  -d '{
    "model": "claude-sonnet-4.5",
    "messages": [
      {"role": "system", "content": "You are a helpful assistant."},
      {"role": "user", "content": "What is the capital of France?"}
    ],
    "temperature": 0.7,
    "max_tokens": 150
  }'
```

**Postman:**
- Method: `POST`
- URL: `http://localhost:8000/v1/chat/completions`
- Headers:
  - `Content-Type`: `application/json`
  - `Authorization`: `Bearer YOUR_GITHUB_COPILOT_TOKEN`
- Body (raw JSON):
```json
{
  "model": "claude-sonnet-4.5",
  "messages": [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "What is the capital of France?"}
  ],
  "temperature": 0.7,
  "max_tokens": 150
}
```

**Response:**
```json
{
  "id": "chatcmpl-abc123",
  "object": "chat.completion",
  "created": 1234567890,
  "model": "claude-sonnet-4.5",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "The capital of France is Paris."
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 20,
    "completion_tokens": 8,
    "total_tokens": 28
  }
}
```

---

### 3. Chat Completion (Streaming)

**Endpoint:** `POST /v1/chat/completions` with `stream: true`

**cURL:**
```bash
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_GITHUB_COPILOT_TOKEN" \
  -d '{
    "model": "claude-sonnet-4.5",
    "messages": [
      {"role": "user", "content": "Count from 1 to 5"}
    ],
    "stream": true,
    "max_tokens": 50
  }'
```

**Postman Body:**
```json
{
  "model": "claude-sonnet-4.5",
  "messages": [
    {"role": "user", "content": "Count from 1 to 5"}
  ],
  "stream": true,
  "max_tokens": 50
}
```

---

### 4. Multi-Turn Conversation

**cURL:**
```bash
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_GITHUB_COPILOT_TOKEN" \
  -d '{
    "model": "claude-sonnet-4.5",
    "messages": [
      {"role": "user", "content": "My favorite color is blue."},
      {"role": "assistant", "content": "I'll remember that your favorite color is blue!"},
      {"role": "user", "content": "What is my favorite color?"}
    ],
    "max_tokens": 50
  }'
```

**Postman Body:**
```json
{
  "model": "claude-sonnet-4.5",
  "messages": [
    {"role": "user", "content": "My favorite color is blue."},
    {"role": "assistant", "content": "I'll remember that your favorite color is blue!"},
    {"role": "user", "content": "What is my favorite color?"}
  ],
  "max_tokens": 50
}
```

---

### 5. Using Model Aliases

**cURL:**
```bash
# Using alias instead of full model name
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_GITHUB_COPILOT_TOKEN" \
  -d '{
    "model": "claude",
    "messages": [
      {"role": "user", "content": "Hello!"}
    ]
  }'
```

**Supported Aliases:**
| Alias | Maps To |
|-------|---------|
| `gpt-4` | `gpt-4.1` |
| `gpt-4-turbo` | `gpt-4o` |
| `claude` | `claude-sonnet-4.5` |
| `claude-3.5-sonnet` | `claude-sonnet-4.5` |

---

## Anthropic-Compatible Endpoints

### 6. Create Message (Non-Streaming)

**Endpoint:** `POST /v1/messages`

**cURL:**
```bash
curl -X POST http://localhost:8000/v1/messages \
  -H "Content-Type: application/json" \
  -H "x-api-key: YOUR_GITHUB_COPILOT_TOKEN" \
  -d '{
    "model": "claude-opus-4.5",
    "max_tokens": 1024,
    "system": "You are a helpful technical assistant.",
    "messages": [
      {"role": "user", "content": "Explain what a REST API is."}
    ]
  }'
```

**Postman:**
- Method: `POST`
- URL: `http://localhost:8000/v1/messages`
- Headers:
  - `Content-Type`: `application/json`
  - `x-api-key`: `YOUR_GITHUB_COPILOT_TOKEN`
- Body (raw JSON):
```json
{
  "model": "claude-opus-4.5",
  "max_tokens": 1024,
  "system": "You are a helpful technical assistant.",
  "messages": [
    {"role": "user", "content": "Explain what a REST API is."}
  ]
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
      "text": "A REST API is a web service that uses HTTP methods..."
    }
  ],
  "model": "claude-opus-4.5",
  "stop_reason": "end_turn",
  "stop_sequence": null,
  "usage": {
    "input_tokens": 25,
    "output_tokens": 100
  }
}
```

---

### 7. Create Message (Streaming)

**Endpoint:** `POST /v1/messages` with `stream: true`

**cURL:**
```bash
curl -X POST http://localhost:8000/v1/messages \
  -H "Content-Type: application/json" \
  -H "x-api-key: YOUR_GITHUB_COPILOT_TOKEN" \
  -d '{
    "model": "claude-sonnet-4.5",
    "max_tokens": 100,
    "messages": [
      {"role": "user", "content": "Tell me a short joke"}
    ],
    "stream": true
  }'
```

**Postman Body:**
```json
{
  "model": "claude-sonnet-4.5",
  "max_tokens": 100,
  "messages": [
    {"role": "user", "content": "Tell me a short joke"}
  ],
  "stream": true
}
```

---

### 8. Message with Temperature

**cURL:**
```bash
curl -X POST http://localhost:8000/v1/messages \
  -H "Content-Type: application/json" \
  -H "x-api-key: YOUR_GITHUB_COPILOT_TOKEN" \
  -d '{
    "model": "claude-sonnet-4.5",
    "max_tokens": 200,
    "temperature": 0.5,
    "messages": [
      {"role": "user", "content": "Write a haiku about coding"}
    ]
  }'
```

**Postman Body:**
```json
{
  "model": "claude-sonnet-4.5",
  "max_tokens": 200,
  "temperature": 0.5,
  "messages": [
    {"role": "user", "content": "Write a haiku about coding"}
  ]
}
```

---

### 9. Multi-Turn Conversation (Anthropic)

**cURL:**
```bash
curl -X POST http://localhost:8000/v1/messages \
  -H "Content-Type: application/json" \
  -H "x-api-key: YOUR_GITHUB_COPILOT_TOKEN" \
  -d '{
    "model": "claude-sonnet-4.5",
    "max_tokens": 500,
    "messages": [
      {"role": "user", "content": "I'm learning Python. Can you help?"},
      {"role": "assistant", "content": "Of course! What specific topic would you like to start with?"},
      {"role": "user", "content": "How do I create a list?"}
    ]
  }'
```

**Postman Body:**
```json
{
  "model": "claude-sonnet-4.5",
  "max_tokens": 500,
  "messages": [
    {"role": "user", "content": "I'm learning Python. Can you help?"},
    {"role": "assistant", "content": "Of course! What specific topic would you like to start with?"},
    {"role": "user", "content": "How do I create a list?"}
  ]
}
```

---

## Authentication Endpoints

### 10. Get Auth Configuration

**Endpoint:** `GET /auth/config`

**cURL:**
```bash
curl -X GET http://localhost:8000/auth/config
```

**Postman:**
- Method: `GET`
- URL: `http://localhost:8000/auth/config`

**Response:**
```json
{
  "mode": "passthrough",
  "api_key_header": "Authorization",
  "api_key_prefix": "Bearer "
}
```

---

### 11. Get Auth Status

**Endpoint:** `GET /auth/status`

**cURL:**
```bash
curl -X GET http://localhost:8000/auth/status
```

---

### 12. Initiate OAuth (Managed Mode Only)

**Endpoint:** `POST /auth/login`

**cURL:**
```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{}'
```

---

### 13. Logout (Managed Mode Only)

**Endpoint:** `POST /auth/logout`

**cURL:**
```bash
curl -X POST http://localhost:8000/auth/logout
```

---

## Utility Endpoints

### 14. Health Check

**Endpoint:** `GET /health`

**cURL:**
```bash
curl -X GET http://localhost:8000/health
```

**Response:**
```json
{
  "status": "healthy",
  "version": "0.1.0"
}
```

---

### 15. Root Info

**Endpoint:** `GET /`

**cURL:**
```bash
curl -X GET http://localhost:8000/
```

**Response:**
```json
{
  "name": "g-copilot-proxy",
  "version": "0.1.0",
  "docs": "/docs",
  "openapi": "/openapi.json",
  "authentication": "passthrough"
}
```

---

## Postman Collection JSON

Copy and import this into Postman:

```json
{
  "info": {
    "name": "g-copilot-proxy",
    "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
  },
  "variable": [
    {
      "key": "base_url",
      "value": "http://localhost:8000"
    },
    {
      "key": "api_key",
      "value": "YOUR_GITHUB_COPILOT_TOKEN"
    }
  ],
  "item": [
    {
      "name": "OpenAI Endpoints",
      "item": [
        {
          "name": "List Models",
          "request": {
            "method": "GET",
            "header": [],
            "url": {
              "raw": "{{base_url}}/v1/models",
              "host": ["{{base_url}}"],
              "path": ["v1", "models"]
            }
          }
        },
        {
          "name": "Chat Completion",
          "request": {
            "method": "POST",
            "header": [
              {"key": "Content-Type", "value": "application/json"},
              {"key": "Authorization", "value": "Bearer {{api_key}}"}
            ],
            "body": {
              "mode": "raw",
              "raw": "{\n  \"model\": \"claude-sonnet-4.5\",\n  \"messages\": [\n    {\"role\": \"user\", \"content\": \"Hello!\"}\n  ]\n}"
            },
            "url": {
              "raw": "{{base_url}}/v1/chat/completions",
              "host": ["{{base_url}}"],
              "path": ["v1", "chat", "completions"]
            }
          }
        },
        {
          "name": "Chat Completion (Streaming)",
          "request": {
            "method": "POST",
            "header": [
              {"key": "Content-Type", "value": "application/json"},
              {"key": "Authorization", "value": "Bearer {{api_key}}"}
            ],
            "body": {
              "mode": "raw",
              "raw": "{\n  \"model\": \"claude-sonnet-4.5\",\n  \"messages\": [\n    {\"role\": \"user\", \"content\": \"Count to 5\"}\n  ],\n  \"stream\": true\n}"
            },
            "url": {
              "raw": "{{base_url}}/v1/chat/completions",
              "host": ["{{base_url}}"],
              "path": ["v1", "chat", "completions"]
            }
          }
        }
      ]
    },
    {
      "name": "Anthropic Endpoints",
      "item": [
        {
          "name": "Create Message",
          "request": {
            "method": "POST",
            "header": [
              {"key": "Content-Type", "value": "application/json"},
              {"key": "x-api-key", "value": "{{api_key}}"}
            ],
            "body": {
              "mode": "raw",
              "raw": "{\n  \"model\": \"claude-sonnet-4.5\",\n  \"max_tokens\": 1024,\n  \"messages\": [\n    {\"role\": \"user\", \"content\": \"Hello!\"}\n  ]\n}"
            },
            "url": {
              "raw": "{{base_url}}/v1/messages",
              "host": ["{{base_url}}"],
              "path": ["v1", "messages"]
            }
          }
        },
        {
          "name": "Create Message (Streaming)",
          "request": {
            "method": "POST",
            "header": [
              {"key": "Content-Type", "value": "application/json"},
              {"key": "x-api-key", "value": "{{api_key}}"}
            ],
            "body": {
              "mode": "raw",
              "raw": "{\n  \"model\": \"claude-sonnet-4.5\",\n  \"max_tokens\": 100,\n  \"messages\": [\n    {\"role\": \"user\", \"content\": \"Tell me a joke\"}\n  ],\n  \"stream\": true\n}"
            },
            "url": {
              "raw": "{{base_url}}/v1/messages",
              "host": ["{{base_url}}"],
              "path": ["v1", "messages"]
            }
          }
        }
      ]
    },
    {
      "name": "Auth Endpoints",
      "item": [
        {
          "name": "Get Auth Status",
          "request": {
            "method": "GET",
            "url": {
              "raw": "{{base_url}}/auth/status",
              "host": ["{{base_url}}"],
              "path": ["auth", "status"]
            }
          }
        },
        {
          "name": "Get Auth Config",
          "request": {
            "method": "GET",
            "url": {
              "raw": "{{base_url}}/auth/config",
              "host": ["{{base_url}}"],
              "path": ["auth", "config"]
            }
          }
        }
      ]
    },
    {
      "name": "Utility",
      "item": [
        {
          "name": "Health Check",
          "request": {
            "method": "GET",
            "url": {
              "raw": "{{base_url}}/health",
              "host": ["{{base_url}}"],
              "path": ["health"]
            }
          }
        }
      ]
    }
  ]
}
```

---

## Importing to Postman

1. Copy the collection JSON above
2. Open Postman
3. Click "Import" in the top left
4. Select "Raw text" and paste the JSON
5. Click "Import"
6. Update the `api_key` variable with your actual GitHub Copilot token

---

## Common Error Responses

### 401 Unauthorized
```json
{
  "detail": "No OAuth credentials found. Please authenticate at /auth/login"
}
```

### 422 Validation Error
```json
{
  "detail": [
    {
      "loc": ["body", "model"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

### 500 Internal Server Error
```json
{
  "detail": "pi-ai bridge error: Connection failed"
}
```

---

## Tips for Postman

1. **Set environment variables** for `base_url` and `api_key` to easily switch between environments

2. **Use tests** to validate responses automatically:
```javascript
pm.test("Status code is 200", function () {
    pm.response.to.have.status(200);
});
```

3. **Enable streaming** in Postman settings (Settings → General → Send and load request data asynchronously)

4. **Save responses** to compare model outputs across different requests
