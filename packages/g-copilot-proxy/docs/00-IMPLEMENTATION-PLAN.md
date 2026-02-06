# g-copilot-proxy Implementation Plan

## Overview

`g-copilot-proxy` is a Python server that exposes OpenAI and Anthropic compatible endpoints, backed by GitHub Copilot via the `@mariozechner/pi-ai` library.

> **IMPORTANT: No commits should be made during implementation.** This is a planning-only repository. All code changes should be made in the actual implementation package, not committed to git during the planning phase.

## Project Goals

1. **OpenAI Compatibility**: Expose `/v1/chat/completions` and `/v1/models` endpoints
2. **Anthropic Compatibility**: Expose `/v1/messages` and `/v1/models` endpoints
3. **GitHub Copilot Backend**: Use `@mariozechner/pi-ai` library to call GitHub Copilot
4. **Streaming Support**: Full SSE streaming for both APIs
5. **Authentication**: Support both API key pass-through and managed OAuth

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         g-copilot-proxy                             │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌──────────────────────┐  ┌──────────────────────┐                 │
│  │  OpenAI Compatible   │  │ Anthropic Compatible │                 │
│  │     Endpoints        │  │     Endpoints        │                 │
│  │  /v1/chat/completions │  │  /v1/messages        │                 │
│  │  /v1/models          │  │  /v1/models          │                 │
│  └──────────┬───────────┘  └──────────┬───────────┘                 │
│             │                         │                              │
│             └──────────┬──────────────┘                              │
│                        │                                             │
│             ┌──────────▼───────────┐                                 │
│             │   Request Mapper     │                                 │
│             │  (normalize & route) │                                 │
│             └──────────┬───────────┘                                 │
│                        │                                             │
│             ┌──────────▼───────────┐                                 │
│             │  pi-ai Bridge Layer  │                                 │
│             │  (calls @mariozechner/pi-ai)                          │
│             └──────────┬───────────┘                                 │
│                        │                                             │
│             ┌──────────▼───────────┐                                 │
│             │   GitHub Copilot     │                                 │
│             │   (via pi-ai lib)    │                                 │
│             └──────────────────────┘                                 │
│                                                                      │
├─────────────────────────────────────────────────────────────────────┤
│  Authentication Layer                                               │
│  - Pass-through: Client sends GitHub Copilot token                   │
│  - Managed: Server handles OAuth flow                                │
└─────────────────────────────────────────────────────────────────────┘
```

## Technology Choice: FastAPI

**FastAPI** is recommended over alternatives:

| Feature | FastAPI | Flask | Django |
|---------|---------|-------|--------|
| Async support | ✅ Native | ❌ Requires extensions | ✅ Since 3.1 |
| OpenAPI docs | ✅ Auto-generated | ❌ Manual | ⚠️ Requires DRF |
| Type validation | ✅ Pydantic | ❌ Manual | ⚠️ Requires DRF |
| Streaming | ✅ Native | ⚠️ Manual | ⚠️ Manual |
| Performance | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ |

## GitHub Copilot Models Available

Via `@mariozechner/pi-ai`:

### Claude Models
- `claude-haiku-4.5` - Claude Haiku 4.5
- `claude-sonnet-4` - Claude Sonnet 4
- `claude-sonnet-4.5` - Claude Sonnet 4.5
- `claude-opus-4.5` - Claude Opus 4.5
- `claude-opus-4.6` - Claude Opus 4.6 (with reasoning)

### Gemini Models
- `gemini-2.5-pro` - Gemini 2.5 Pro
- `gemini-3-flash-preview` - Gemini 3 Flash Preview
- `gemini-3-pro-preview` - Gemini 3 Pro Preview

### GPT Models
- `gpt-4.1` - GPT 4.1
- `gpt-4o` - GPT 4o
- `gpt-5` - GPT 5 (with reasoning)
- `gpt-5.1` - GPT 5.1 (with reasoning)
- `gpt-5.2` - GPT 5.2 (with reasoning)
- `gpt-5.3` - GPT 5.3 (with reasoning)

### Code Models
- `gpt-5.1-codex` - GPT 5.1 Codex (with reasoning)

### Grok Models
- `grok-code-fast-1` - Grok Code Fast 1

## Key Data Types from pi-ai

### Context (Request)
```typescript
interface Context {
  systemPrompt?: string;
  messages: Message[];
  tools?: Tool[];
}
```

### Message Types
```typescript
type UserMessage = {
  role: "user";
  content: string | Array<{type: "text" | "image", text?: string, data?: string, mimeType?: string}>;
  timestamp: number;
}

type AssistantMessage = {
  role: "assistant";
  content: Array<{type: "text" | "thinking" | "toolCall", ...}>;
  api: Api;
  provider: Provider;
  model: string;
  usage: Usage;
  stopReason: StopReason;
  timestamp: number;
}

type ToolResultMessage = {
  role: "toolResult";
  toolCallId: string;
  toolName: string;
  content: Array<{type: "text" | "image", ...}>;
  isError: boolean;
  timestamp: number;
}
```

### Streaming Events
```typescript
type AssistantMessageEvent =
  | { type: "start"; partial: AssistantMessage }
  | { type: "text_delta"; contentIndex: number; delta: string; partial: AssistantMessage }
  | { type: "text_end"; contentIndex: number; content: string; partial: AssistantMessage }
  | { type: "thinking_delta"; contentIndex: number; delta: string; partial: AssistantMessage }
  | { type: "thinking_end"; contentIndex: number; content: string; partial: AssistantMessage }
  | { type: "toolcall_start"; contentIndex: number; partial: AssistantMessage }
  | { type: "toolcall_delta"; contentIndex: number; delta: string; partial: AssistantMessage }
  | { type: "toolcall_end"; contentIndex: number; toolCall: ToolCall; partial: AssistantMessage }
  | { type: "done"; reason: StopReason; message: AssistantMessage }
  | { type: "error"; reason: StopReason; error: AssistantMessage };
```

## Implementation Phases

1. **[Phase 1: Project Setup](./01-PHASE-1-SETUP.md)** - Project structure, dependencies, base configuration
2. **[Phase 2: OpenAI Endpoints](./02-PHASE-2-OPENAI.md)** - OpenAI-compatible API implementation
3. **[Phase 3: Anthropic Endpoints](./03-PHASE-3-ANTHROPIC.md)** - Anthropic Messages API implementation
4. **[Phase 4: Authentication](./04-PHASE-4-AUTH.md)** - OAuth and API key management
5. **[Phase 5: Testing & Deployment](./05-PHASE-5-TESTING.md)** - Testing, Docker, and deployment

## Quick Start Reference

### Using pi-ai from Python

```python
import subprocess
import json

# Call Node.js pi-ai library
def get_copilot_response(model_id: str, messages: list, tools: list = None):
    payload = {
        "model": model_id,
        "context": {
            "messages": messages,
            "tools": tools or []
        }
    }

    result = subprocess.run(
        ["node", "-e", """
        const { getModel, stream } = require('@mariozechner/pi-ai');
        const input = JSON.parse(require('fs').readFileSync(0, 'utf-8'));
        const model = getModel('github-copilot', input.model);
        const context = input.context;
        const s = stream(model, context);
        (async () => {
            for await (const event of s) {
                console.log(JSON.stringify(event));
            }
        })();
        """],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        cwd="../ai"  # Path to ai package
    )

    return [json.loads(line) for line in result.stdout.strip().split('\n') if line]
```

### Directory Structure

```
g-copilot-proxy/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI application entry
│   ├── config.py               # Configuration settings
│   ├── api/
│   │   ├── __init__.py
│   │   ├── openai/             # OpenAI compatible routes
│   │   │   ├── __init__.py
│   │   │   ├── chat.py         # /v1/chat/completions
│   │   │   └── models.py       # /v1/models
│   │   └── anthropic/          # Anthropic compatible routes
│   │       ├── __init__.py
│   │       ├── messages.py     # /v1/messages
│   │       └── models.py       # /v1/models
│   ├── core/
│   │   ├── __init__.py
│   │   ├── piai_bridge.py      # Bridge to @mariozechner/pi-ai
│   │   ├── mapper.py           # Request/response mapping
│   │   └── streaming.py        # SSE streaming utilities
│   └── auth/
│       ├── __init__.py
│       ├── github_copilot.py   # GitHub Copilot OAuth
│       └── middleware.py       # Auth middleware
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_openai_api.py
│   ├── test_anthropic_api.py
│   └── test_piai_bridge.py
├── scripts/
│   ├── setup_oauth.js          # OAuth setup helper
│   └── dev.sh                  # Development server
├── pyproject.toml              # Poetry dependencies
├── Dockerfile
├── .env.example
└── README.md
```

## Next Steps

Proceed to [Phase 1: Project Setup](./01-PHASE-1-SETUP.md) to begin implementation.
