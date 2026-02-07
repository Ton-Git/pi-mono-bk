# REST Client VS Code Extension Examples

Save the content below as `g-copilot-proxy.http` and use with the [REST Client](https://marketplace.visualstudio.com/items?itemName=humao.rest-client) VS Code extension.

## Base URL
```
@baseUrl = http://localhost:8000
```

---

## g-copilot-proxy.http

```http
### =============================================================================
### g-copilot-proxy API Test Collection
### REST Client file for testing g-copilot-proxy endpoints
### Base URL: {{baseUrl}}
### =============================================================================

@baseUrl = http://localhost:8000
@modelName = gpt-5-mini

###############################################################################
# HEALTH CHECK ENDPOINTS
###############################################################################

### 1. Root Endpoint - Get server info
GET {{baseUrl}}/

### 2. Health Check
GET {{baseUrl}}/health

###############################################################################
# AUTHENTICATION ENDPOINTS
###############################################################################

### 3. Login - Initiate GitHub Device OAuth flow
GET {{baseUrl}}/auth/login

### 4. Logout - Clear stored credentials
POST {{baseUrl}}/auth/logout

###############################################################################
# OPENAI-COMPATIBLE ENDPOINTS
###############################################################################

### 5. List Models (OpenAI format)
GET {{baseUrl}}/v1/models

### 6. Get Specific Model (OpenAI format)
GET {{baseUrl}}/v1/models/{{modelName}}

### 7. Chat Completion - Simple (OpenAI format)
POST {{baseUrl}}/v1/chat/completions
Content-Type: application/json

{
  "model": "{{modelName}}",
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

### 8. Chat Completion - Streaming (OpenAI format)
POST {{baseUrl}}/v1/chat/completions
Content-Type: application/json

{
  "model": "{{modelName}}",
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

### 9. Chat Completion - With Tools (OpenAI format)
POST {{baseUrl}}/v1/chat/completions
Content-Type: application/json

{
  "model": "{{modelName}}",
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

### 10. Chat Completion - With Image (OpenAI format)
POST {{baseUrl}}/v1/chat/completions
Content-Type: application/json

{
  "model": "{{modelName}}",
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

### 11. Chat Completion - Multi-turn Conversation (OpenAI format)
POST {{baseUrl}}/v1/chat/completions
Content-Type: application/json

{
  "model": "{{modelName}}",
  "messages": [
    {
      "role": "system",
      "content": "You are a helpful coding assistant."
    },
    {
      "role": "user",
      "content": "How do I reverse a string in JavaScript?"
    },
    {
      "role": "assistant",
      "content": "You can reverse a string in JavaScript using several methods. Here's a simple approach:"
    },
    {
      "role": "user",
      "content": "Can you show me the code?"
    }
  ],
  "stream": false,
  "temperature": 0.5,
  "max_tokens": 300
}

### 12. Chat Completion - With System Message (OpenAI format)
POST {{baseUrl}}/v1/chat/completions
Content-Type: application/json

{
  "model": "{{modelName}}",
  "messages": [
    {
      "role": "system",
      "content": "You are a senior software engineer. Provide concise, technical answers with code examples when appropriate."
    },
    {
      "role": "user",
      "content": "What's the difference between `let` and `const` in JavaScript?"
    }
  ],
  "stream": false,
  "temperature": 0.3,
  "max_tokens": 400
}

###############################################################################
# ANTHROPIC-COMPATIBLE ENDPOINTS
###############################################################################

### 13. List Models (Anthropic format)
GET {{baseUrl}}/v1/models

### 14. Message - Simple (Anthropic format)
POST {{baseUrl}}/v1/messages
Content-Type: application/json
Anthropic-Version: 2023-06-01

{
  "model": "claude-3-5-sonnet-20241022",
  "max_tokens": 500,
  "messages": [
    {
      "role": "user",
      "content": "Hello! Can you explain what REST APIs are?"
    }
  ],
  "temperature": 0.7
}

### 15. Message - With System Prompt (Anthropic format)
POST {{baseUrl}}/v1/messages
Content-Type: application/json
Anthropic-Version: 2023-06-01

{
  "model": "claude-3-5-sonnet-20241022",
  "max_tokens": 500,
  "messages": [
    {
      "role": "user",
      "content": "Explain the concept of recursion in programming."
    }
  ],
  "system": "You are a helpful technical assistant who provides clear explanations with examples.",
  "temperature": 0.6
}

### 16. Message - Streaming (Anthropic format)
POST {{baseUrl}}/v1/messages
Content-Type: application/json
Anthropic-Version: 2023-06-01

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

### 17. Message - With Tools (Anthropic format)
POST {{baseUrl}}/v1/messages
Content-Type: application/json
Anthropic-Version: 2023-06-01

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

### 18. Message - With Image (Anthropic format)
POST {{baseUrl}}/v1/messages
Content-Type: application/json
Anthropic-Version: 2023-06-01

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

### 19. Message - Multi-turn Conversation (Anthropic format)
POST {{baseUrl}}/v1/messages
Content-Type: application/json
Anthropic-Version: 2023-06-01

{
  "model": "claude-3-5-sonnet-20241022",
  "max_tokens": 400,
  "messages": [
    {
      "role": "user",
      "content": "How do I create a React component?"
    },
    {
      "role": "assistant",
      "content": "To create a React component, you can use either function components or class components. Function components are the modern approach."
    },
    {
      "role": "user",
      "content": "Show me a function component example"
    }
  ],
  "temperature": 0.5
}

### 20. Message - With Top P (Anthropic format)
POST {{baseUrl}}/v1/messages
Content-Type: application/json
Anthropic-Version: 2023-06-01

{
  "model": "claude-3-5-sonnet-20241022",
  "max_tokens": 200,
  "messages": [
    {
      "role": "user",
      "content": "Give me a brief overview of TypeScript"
    }
  ],
  "top_p": 0.9,
  "temperature": 0.7
}

###############################################################################
# EDGE CASES AND ERROR TESTING
###############################################################################

### 21. Chat Completion - Empty Messages Array (should error)
POST {{baseUrl}}/v1/chat/completions
Content-Type: application/json

{
  "model": "{{modelName}}",
  "messages": [],
  "stream": false
}

### 22. Chat Completion - Invalid Model Name (tests alias resolution)
POST {{baseUrl}}/v1/chat/completions
Content-Type: application/json

{
  "model": "invalid-model-name",
  "messages": [
    {
      "role": "user",
      "content": "Hello"
    }
  ],
  "stream": false
}

### 23. Chat Completion - Very Long Message (tests max_tokens)
POST {{baseUrl}}/v1/chat/completions
Content-Type: application/json

{
  "model": "{{modelName}}",
  "messages": [
    {
      "role": "user",
      "content": "Tell me a very long story about a dragon who lived in a mountain. Include details about the dragon's appearance, its daily routine, and its interactions with other creatures."
    }
  ],
  "stream": false,
  "max_tokens": 50
}

### 24. Message - Missing max_tokens (should error - Anthropic requires this)
POST {{baseUrl}}/v1/messages
Content-Type: application/json
Anthropic-Version: 2023-06-01

{
  "model": "claude-3-5-sonnet-20241022",
  "messages": [
    {
      "role": "user",
      "content": "Hello"
    }
  ]
}

###############################################################################
# MODEL ALIAS TESTING
###############################################################################

### 25. Chat Completion - Using gpt-4 alias (maps to claude-sonnet-4.5)
POST {{baseUrl}}/v1/chat/completions
Content-Type: application/json

{
  "model": "gpt-4",
  "messages": [
    {
      "role": "user",
      "content": "What model are you using?"
    }
  ],
  "stream": false
}

### 26. Chat Completion - Using gpt-4o alias (maps to claude-sonnet-4.5)
POST {{baseUrl}}/v1/chat/completions
Content-Type: application/json

{
  "model": "gpt-4o",
  "messages": [
    {
      "role": "user",
      "content": "What is 2 + 2?"
    }
  ],
  "stream": false
}

### 27. Chat Completion - Using gpt-3.5-turbo alias (maps to gpt-4.1)
POST {{baseUrl}}/v1/chat/completions
Content-Type: application/json

{
  "model": "gpt-3.5-turbo",
  "messages": [
    {
      "role": "user",
      "content": "Say hello in three different languages"
    }
  ],
  "stream": false
}

### 28. Message - Using claude-3-opus alias (maps to claude-opus-4.5)
POST {{baseUrl}}/v1/messages
Content-Type: application/json
Anthropic-Version: 2023-06-01

{
  "model": "claude-3-opus",
  "max_tokens": 200,
  "messages": [
    {
      "role": "user",
      "content": "What is your model name?"
    }
  ]
}

###############################################################################
# TEMPERATURE AND SAMPLING TESTING
###############################################################################

### 29. Chat Completion - Low Temperature (more deterministic)
POST {{baseUrl}}/v1/chat/completions
Content-Type: application/json

{
  "model": "{{modelName}}",
  "messages": [
    {
      "role": "user",
      "content": "Complete this sentence: The quick brown fox..."
    }
  ],
  "stream": false,
  "temperature": 0.1,
  "max_tokens": 50
}

### 30. Chat Completion - High Temperature (more creative)
POST {{baseUrl}}/v1/chat/completions
Content-Type: application/json

{
  "model": "{{modelName}}",
  "messages": [
    {
      "role": "user",
      "content": "Write a creative opening line for a sci-fi novel"
    }
  ],
  "stream": false,
  "temperature": 1.5,
  "max_tokens": 100
}

### 31. Chat Completion - With Top P sampling
POST {{baseUrl}}/v1/chat/completions
Content-Type: application/json

{
  "model": "{{modelName}}",
  "messages": [
    {
      "role": "user",
      "content": "Explain quantum computing in simple terms"
    }
  ],
  "stream": false,
  "temperature": 0.7,
  "top_p": 0.9,
  "max_tokens": 200
}

###############################################################################
# CODE GENERATION EXAMPLES
###############################################################################

### 32. Chat Completion - Generate Python Function
POST {{baseUrl}}/v1/chat/completions
Content-Type: application/json

{
  "model": "{{modelName}}",
  "messages": [
    {
      "role": "system",
      "content": "You are a coding assistant. Provide clean, well-commented code."
    },
    {
      "role": "user",
      "content": "Write a Python function that checks if a number is prime"
    }
  ],
  "stream": false,
  "temperature": 0.3,
  "max_tokens": 300
}

### 33. Chat Completion - Generate SQL Query
POST {{baseUrl}}/v1/chat/completions
Content-Type: application/json

{
  "model": "{{modelName}}",
  "messages": [
    {
      "role": "user",
      "content": "Write a SQL query to find the top 5 customers by total order amount from tables: customers(id, name) and orders(customer_id, amount)"
    }
  ],
  "stream": false,
  "temperature": 0.2,
  "max_tokens": 200
}

### 34. Message - Generate React Component (Anthropic)
POST {{baseUrl}}/v1/messages
Content-Type: application/json
Anthropic-Version: 2023-06-01

{
  "model": "claude-3-5-sonnet-20241022",
  "max_tokens": 500,
  "messages": [
    {
      "role": "user",
      "content": "Create a React component for a simple counter button with increment and decrement functionality"
    }
  ],
  "system": "You are a frontend developer. Write clean, modern React code with hooks.",
  "temperature": 0.3
}
```

---

## How to Use

1. Install the [REST Client](https://marketplace.visualstudio.com/items?itemName=humao.rest-client) extension in VS Code
2. Copy the content inside the code block above
3. Save it as `g-copilot-proxy.http` in your project
4. Click "Send Request" above each request, or use the shortcut `Ctrl+Alt+R` / `Cmd+Alt+R`

## Features

- **Variables**: Use `@baseUrl` and `@modelName` at the top to easily configure your endpoint
- **Comments**: Use `#` or `###` for comments and request separators
- **Multiple Requests**: All requests in one file, easily switch between them
- **Response Viewer**: Responses appear in a separate panel with syntax highlighting

---

## Model Aliases Reference

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

---

## Authentication Setup

Before testing API endpoints:

1. Visit `http://localhost:8000/auth/login` in your browser
2. Complete the GitHub device authorization flow
3. Credentials are stored automatically - no auth headers needed in requests
