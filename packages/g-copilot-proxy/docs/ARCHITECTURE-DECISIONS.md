# Architecture Decision Records

This document records significant architectural decisions for `g-copilot-proxy`.

## ADR-001: Use FastAPI Framework

**Status:** Accepted

**Context:**
We need a Python web framework to build the proxy server that supports async operations, streaming responses, and automatic API documentation.

**Decision:**
Use FastAPI as the web framework.

**Rationale:**

| Factor | FastAPI | Flask | Django |
|--------|---------|-------|--------|
| Native async support | ✅ Yes | ❌ Requires extension | ✅ Since 3.1 |
| Automatic OpenAPI docs | ✅ Yes | ❌ Manual | ⚠️ Requires DRF |
| Pydantic validation | ✅ Built-in | ❌ Manual | ⚠️ Requires DRF |
| Streaming SSE | ✅ Native | ⚠️ Manual | ⚠️ Manual |
| Performance | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ |
| Learning curve | Low | Low | High |

**Consequences:**

*Positive:*
- Automatic OpenAPI/Swagger documentation at `/docs`
- Type validation via Pydantic prevents invalid requests
- Native async support for high concurrency
- Excellent performance with Starlette backbone
- Easy dependency injection system

*Negative:*
- Newer framework with smaller ecosystem than Flask/Django
- Fewer third-party extensions available

**Alternatives Considered:**
- **Flask:** More mature but requires additional libraries for async, OpenAPI, and validation
- **Django REST Framework:** Heavy for a simple proxy, more complex setup

**Related Decisions:** ADR-002 (Python vs Node.js), ADR-003 (Bridge Architecture)

---

## ADR-002: Python with Node.js Subprocess

**Status:** Accepted

**Context:**
The `@mariozechner/pi-ai` library is written in TypeScript/Node.js. We need to decide whether to:
1. Write the entire proxy in Node.js
2. Write the proxy in Python and call pi-ai via subprocess

**Decision:**
Write the proxy in Python (FastAPI) and communicate with pi-ai via Node.js subprocess.

**Rationale:**

**Advantages of Python approach:**
- Broader API compatibility with existing Python tools (OpenAI/Anthropic SDKs have first-class Python support)
- Easier deployment in Python environments (many enterprises use Python for AI/ML services)
- Better async/await patterns for streaming SSE
- Simpler integration with monitoring/observability tools in Python ecosystem

**Advantages of subprocess bridge:**
- Clean separation between proxy logic and pi-ai library
- Can update pi-ai independently without changing proxy code
- Node.js remains isolated, reducing dependency conflicts

**Consequences:**

*Positive:*
- Leverages existing Python AI/ML ecosystem
- Clean module boundaries
- Easier to maintain for Python developers

*Negative:*
- Subprocess communication adds latency (~10-50ms per request)
- Need to handle Node.js process lifecycle
- Additional dependency on Node.js runtime

**Mitigations:**
- Use stdin/stdout for efficient JSON communication
- Reuse Node.js processes where possible
- Cache model lists to reduce subprocess calls

**Alternatives Considered:**
- **Pure Node.js proxy:** Would eliminate subprocess overhead but less compatible with existing Python tooling
- **Pure Python with HTTP wrapper:** Add HTTP layer between proxy and pi-ai, but adds network overhead

**Related Decisions:** ADR-001 (FastAPI), ADR-003 (Bridge Architecture)

---

## ADR-003: Subprocess Bridge Architecture

**Status:** Accepted

**Context:**
We need to communicate between Python and Node.js. Options include:
1. HTTP REST wrapper around pi-ai
2. Direct subprocess with stdin/stdout
3. Message queue (Redis, etc.)

**Decision:**
Use direct subprocess with JSON over stdin/stdout.

**Rationale:**

| Approach | Latency | Complexity | Scalability |
|----------|---------|------------|-------------|
| HTTP wrapper | ~50-100ms | High | High |
| Subprocess stdin/stdout | ~10-30ms | Low | Medium |
| Message queue | ~20-50ms | Very High | Very High |

**Subprocess advantages:**
- Lowest latency for single-server deployment
- No additional infrastructure needed
- Simple JSON communication protocol
- Easy to debug (can see all input/output)

**Consequences:**

*Positive:*
- Minimal latency overhead
- Simple deployment (no additional services)
- Easy to test locally
- Clear communication via JSON

*Negative:*
- One subprocess per request (or need pooling)
- Node.js crashes can affect proxy
- Harder to scale horizontally

**Mitigations:**
- Implement subprocess pooling for production
- Health checks and automatic restart
- Consider HTTP wrapper for multi-instance deployments

**Alternatives Considered:**
- **HTTP wrapper:** Adds network overhead but easier to scale
- **Message queue:** Overkill for single-server deployment

**Related Decisions:** ADR-002 (Python with Node.js)

---

## ADR-004: Dual API Compatibility (OpenAI + Anthropic)

**Status:** Accepted

**Context:**
Clients may want to use either OpenAI or Anthropic SDKs. We need to decide:
1. Support only one format
2. Support both formats
3. Support multiple formats

**Decision:**
Support both OpenAI and Anthropic API formats on the same endpoints.

**Rationale:**

**Benefits of dual support:**
- Users can use existing SDKs without modification
- Broader compatibility with tools that only support one format
- Competitive advantage over single-format proxies
- Minimal code duplication (95% shared logic)

**Implementation approach:**
- Separate request/response models for each format
- Shared mapper layer converts to/from pi-ai format
- Unified streaming response generation

**Consequences:**

*Positive:*
- Maximum client compatibility
- Shared core logic reduces maintenance burden
- Easy to add more formats in future (Google Gemini, etc.)

*Negative:*
- More complex request validation
- Need to maintain mapping logic for each format
- Slightly larger codebase

**Alternatives Considered:**
- **OpenAI-only:** Simpler but limits usability
- **Format negotiation:** Client specifies format in header, but adds complexity

**Related Decisions:** ADR-005 (Request Mapper Pattern)

---

## ADR-005: Request Mapper Pattern

**Status:** Accepted

**Context:**
We need to convert between OpenAI/Anthropic formats and pi-ai format. Options:
1. Inline conversion in endpoints
2. Separate mapper classes
3. Adapter pattern with transformers

**Decision:**
Use separate mapper classes (`OpenAIMapper`, `AnthropicMapper`) with static methods.

**Rationale:**

**Advantages of mapper pattern:**
- Clean separation of concerns
- Easy to test mappers independently
- Can add new formats without touching endpoints
- Clear conversion logic in one place

**Code organization:**
```
app/core/mapper.py
├── OpenAIMapper
│   ├── map_openai_to_piai_messages()
│   ├── map_piai_event_to_openai_chunk()
│   └── map_piai_message_to_openai()
└── AnthropicMapper
    ├── map_anthropic_to_piai_messages()
    ├── map_piai_event_to_anthropic_chunk()
    └── map_piai_message_to_anthropic()
```

**Consequences:**

*Positive:*
- Single responsibility principle
- Easy to unit test
- Clear data flow

*Negative:*
- More files/classes
- Need to maintain multiple conversion paths

**Alternatives Considered:**
- **Inline conversion:** Simpler but harder to test/maintain
- **Generic adapter:** More flexible but over-engineered for 2 formats

**Related Decisions:** ADR-004 (Dual API Compatibility)

---

## ADR-006: Authentication Modes

**Status:** Accepted

**Context:**
Different deployment scenarios have different authentication needs:
- Development: May want to pass through personal tokens
- Production: May want managed OAuth with centralized credentials
- Enterprise: May want SSO integration

**Decision:**
Support pluggable authentication modes via configuration, starting with:
1. **Pass-through mode:** Client sends GitHub Copilot token
2. **Managed mode:** Server handles OAuth flow

**Rationale:**

**Pass-through mode:**
- Simplest for development
- No server-side credential storage
- Client retains full control

**Managed mode:**
- Better for production deployments
- Single OAuth flow for all users
- Easier credential rotation
- Can add SSO later

**Configuration:**
```bash
AUTH_MODE=passthrough|managed
```

**Consequences:**

*Positive:*
- Flexibility for different deployment scenarios
- Simple default (pass-through)
- Clear upgrade path to managed mode

*Negative:**
- Need to maintain two code paths
- Managed mode adds complexity

**Future considerations:**
- Add SSO/SAML support for enterprise
- Add API key authentication (generate proxy-specific keys)
- Add rate limiting per authenticated user

**Alternatives Considered:**
- **OAuth-only:** Too complex for development
- **API key-only:** Doesn't integrate with GitHub Copilot OAuth

**Related Decisions:** ADR-007 (Credential Storage)

---

## ADR-007: Credential Storage

**Status:** Accepted

**Context:**
In managed mode, we need to store OAuth credentials. Options:
1. File-based storage
2. Database
3. Secret management service

**Decision:**
Start with file-based storage (`.copilot-auth.json`), design for database migration.

**Rationale:**

**File-based storage (initial):**
- Simple for single-server deployments
- No external dependencies
- Sufficient for initial release
- Easy to implement and debug

**Database (future):**
- Required for multi-instance deployments
- Better for credential rotation
- Enables audit logging
- Supports multiple user accounts

**Consequences:**

*Positive:*
- Fast to implement
- No database setup required for initial users
- Simple backup/snapshot

*Negative:**
- Doesn't scale to multiple instances
- File permissions need careful configuration
- No built-in audit trail

**Migration path:**
```python
# Abstract credential storage
class CredentialStorage(ABC):
    @abstractmethod
    async def get_credentials(self) -> Optional[dict]: ...

    @abstractmethod
    async def save_credentials(self, credentials: dict): ...

class FileCredentialStorage(CredentialStorage): ...

class DatabaseCredentialStorage(CredentialStorage): ...  # Future
```

**Alternatives Considered:**
- **Database from start:** Over-engineering for initial release
- **Secret service (Vault):** Too complex for initial deployment

**Related Decisions:** ADR-006 (Authentication Modes)

---

## ADR-008: Streaming Response Format

**Status:** Accepted

**Context:**
OpenAI and Anthropic use different SSE formats. We need to decide:
1. Use one format for all responses
2. Match the format based on request type
3. Support format negotiation

**Decision:**
Match the SSE format to the API style (OpenAI format for `/v1/chat/completions`, Anthropic format for `/v1/messages`).

**Rationale:**

**Format matching:**
- Maintains compatibility with existing SDKs
- Clients expect specific SSE formats for each API
- Clear separation of concerns

**OpenAI SSE format:**
```
data: {"id":"chatcmpl-123","choices":[{...}]}

data: [DONE]
```

**Anthropic SSE format:**
```
event: message_start
data: {"type":"message_start",...}

event: content_block_delta
data: {"type":"content_block_delta",...}

event: message_stop
data: {"type":"message_stop"}
```

**Consequences:**

*Positive:*
- Drop-in compatible with official SDKs
- Clear expectations for each endpoint
- Easier debugging (format matches endpoint)

*Negative:*
- Need separate streaming generators for each format
- More code to maintain

**Alternatives Considered:**
- **Unified format:** Simpler but breaks SDK compatibility
- **Format header:** Client specifies format, but adds complexity

**Related Decisions:** ADR-004 (Dual API Compatibility), ADR-005 (Mapper Pattern)

---

## ADR-009: Model Alias System

**Status:** Accepted

**Context:**
GitHub Copilot uses specific model IDs (e.g., `claude-sonnet-4.5`), but users may expect common aliases (e.g., `gpt-4`, `claude-3.5-sonnet`).

**Decision:**
Implement model alias mapping to improve user experience.

**Rationale:**

**Benefits:**
- Users can use familiar model names
- Code is more portable across different providers
- Easier migration from other services

**Implementation:**
```python
MODEL_ALIASES = {
    # OpenAI aliases
    "gpt-4": "gpt-4.1",
    "gpt-4-turbo": "gpt-4o",

    # Claude aliases
    "claude-3.5-sonnet": "claude-sonnet-4.5",
    "claude": "claude-sonnet-4.5",  # Default

    # Generic
    "default": "claude-sonnet-4.5",
}
```

**Consequences:**

*Positive:*
- Better user experience
- Backward compatibility with code using old model names
- Clear default model selection

*Negative:**
- Need to maintain alias mappings
- Potential confusion if aliases shadow real models

**Alternatives Considered:**
- **No aliases:** Users must use exact model IDs
- **Configurable aliases:** Allow users to define custom aliases (future enhancement)

**Related Decisions:** None

---

## ADR-010: Error Handling Strategy

**Status:** Accepted

**Context:**
We need to decide how to handle errors from:
1. Invalid client requests
2. pi-ai bridge failures
3. GitHub Copilot API errors

**Decision:**
Use HTTP status codes with JSON error details. Propagate Copilot errors as 500s with safe messages.

**Rationale:**

**HTTP Status Codes:**
| Status | Usage |
|--------|-------|
| 400 | Invalid request parameters |
| 401 | Missing/invalid authentication |
| 422 | Request validation errors |
| 500 | Server/proxy errors (including pi-ai failures) |

**Error response format:**
```json
{
  "detail": "Human-readable error message"
}
```

**For pi-ai/Copilot errors:**
- Log full error details server-side
- Return generic error message to client
- Don't expose internal implementation details

**Consequences:**

*Positive:*
- Standard HTTP semantics
- Safe error messages (no info leakage)
- Easy to integrate with error tracking

*Negative:**
- Generic errors may be less helpful for debugging

**Alternatives Considered:**
- **Pass-through Copilot errors:** More informative but may leak implementation
- **Custom error codes:** More flexible but non-standard

**Related Decisions:** ADR-003 (Bridge Architecture)

---

## ADR-011: Docker Multi-Stage Build

**Status:** Accepted

**Context:**
We need to distribute the proxy as a Docker container. Options:
1. Single-stage build (include build tools)
2. Multi-stage build (separate build/runtime)
3. Distroless images

**Decision:**
Use multi-stage build with Python slim base.

**Rationale:**

**Multi-stage build benefits:**
- Smaller final image (~200MB vs ~500MB)
- No build tools in runtime (security)
- Clear separation of build/runtime dependencies

**Image structure:**
```dockerfile
# Stage 1: Builder
FROM python:3.11-slim AS builder
# Install Poetry, build dependencies

# Stage 2: Runtime
FROM python:3.11-slim
# Copy only runtime dependencies
```

**Consequences:**

*Positive:*
- Smaller images = faster pulls
- Reduced attack surface (no build tools)
- Professional Docker practice

*Negative:**
- Slightly more complex Dockerfile
- Longer build time (two stages)

**Alternatives Considered:**
- **Single-stage:** Simpler but larger images
- **Distroless:** Smallest but harder debugging

**Related Decisions:** None

---

## ADR-012: Monitoring with Prometheus

**Status:** Accepted

**Context:**
Production deployments need observability. Options:
1. Structured logging only
2. Prometheus metrics
3. OpenTelemetry
4. Commercial APM

**Decision:**
Use Prometheus for metrics, structured JSON logging.

**Rationale:**

**Prometheus advantages:**
- Industry standard for metrics
- Simple pull-based scraping
- Excellent Grafana integration
- Low overhead

**Metrics to track:**
- Request count (by endpoint, status)
- Request duration (histogram)
- Active requests (gauge)
- Copilot API requests (by model, status)

**Consequences:**

*Positive:*
- Standard observability stack
- Easy to set up dashboards
- Low performance impact

*Negative:**
- Need to run Prometheus server (or use managed service)
- Pull-based requires network access

**Future:**
- Add OpenTelemetry tracing
- Add structured logging correlation IDs
- Add RED (Rate, Errors, Duration) metrics

**Alternatives Considered:**
- **OpenTelemetry from start:** More complete but higher complexity
- **Logging only:** Insufficient for production monitoring

**Related Decisions:** None

---

## ADR-013: Configuration via Environment Variables

**Status:** Accepted

**Context:**
Application configuration needs to be flexible. Options:
1. Environment variables
2. Config files (YAML, TOML)
3. Command-line arguments
4. Remote configuration service

**Decision:**
Use environment variables with Pydantic Settings, support `.env` files.

**Rationale:**

**Environment variables:**
- Container-native (Docker/Kubernetes friendly)
- Simple to override per deployment
- No need to mount config files
- Industry standard (12-factor app)

**Pydantic Settings benefits:**
- Type validation
- Automatic casting (strings to int, bool, etc.)
- Default values
- Optional values

**Example:**
```python
class Settings(BaseSettings):
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False

    class Config:
        env_file = ".env"
```

**Consequences:**

*Positive:*
- Container-friendly
- Type-safe configuration
- Easy to document

*Negative:**
- No complex nested structures (use JSON strings for that)
- Need to document all env vars

**Alternatives Considered:**
- **YAML config:** More expressive but requires file mounting
- **Config service:** Overkill for initial release

**Related Decisions:** None

---

## Decision Template

For future architectural decisions, use this template:

```markdown
## ADR-XXX: [Decision Title]

**Status:** Proposed | Accepted | Deprecated | Superseded

**Context:**
[Describe the problem or situation that requires a decision]

**Decision:**
[State the decision clearly]

**Rationale:**
[Explain the reasoning, including pros/cons of alternatives]

**Consequences:**
[Describe the results of this decision, including positive and negative effects]

**Alternatives Considered:**
[List alternative approaches that were considered and why they were not chosen]

**Related Decisions:** [Link to related ADRs]
```

---

## Changelog

| Date | Decision | Status | Change |
|------|----------|--------|--------|
| 2025-02-06 | ADR-001 through ADR-013 | Accepted | Initial architecture decisions |
