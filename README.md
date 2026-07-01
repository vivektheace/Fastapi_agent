
````markdown
# FastAPI LangChain Dynamic Agent API

A small FastAPI project that creates and runs a LangChain agent dynamically at request time.

The API exposes a single main endpoint:

- `POST /agent/run`

The endpoint accepts:

- `agent_type`
- `query`
- optional `tools`

Based on the request, the application selects a system prompt and tools, creates a LangChain agent, runs the query, and returns a structured JSON response.

---

## Core Idea

The goal of this project is to demonstrate:

```text
FastAPI request
→ validate request with Pydantic
→ select prompt and tools based on agent_type
→ create LangChain agent dynamically
→ run the agent
→ return structured JSON response
```

If an API key is configured, the API runs a live LangChain agent.

If no API key is configured, the API uses a deterministic mock fallback so the endpoint can still be tested locally without exposing secrets.

---

## Architecture

```text
Client / Swagger / curl
        ↓
FastAPI route: POST /agent/run
        ↓
Service layer
        ↓
Dynamic agent factory
        ↓
Prompt + tools selected by agent_type
        ↓
LangChain create_agent()
        ↓
LLM response or mock fallback
        ↓
Structured JSON response
```

---

## Project Structure

```text
app/
├── __init__.py
├── agent.py       # Dynamic LangChain agent factory, tools, mock fallback
├── config.py      # Environment-based settings
├── main.py        # FastAPI app entry point and /health
├── models.py      # Pydantic request/response schemas
├── routes.py      # API routes
└── services.py    # Orchestration between route and agent layer

tests/
├── __init__.py
├── conftest.py
└── test_agent.py

.env.example
.gitignore
pyproject.toml
uv.lock
README.md
```

---

## Tech Stack

- Python 3.10+
- FastAPI
- Uvicorn
- Pydantic
- pydantic-settings
- LangChain
- langchain-openai
- pytest
- uv

---

## API Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/health` | Service health check |
| POST | `/agent/run` | Dynamically create and run a LangChain agent |

---

## Request Format

```json
{
  "agent_type": "support",
  "query": "What is the refund policy?",
  "tools": []
}
```

### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `agent_type` | string | No | Type of agent to create. Supported examples: `general`, `math`, `text`, `support` |
| `query` | string | Yes | User question or task |
| `tools` | list[string] | No | Optional extra tools to attach dynamically |

---

## Supported Agent Types

| Agent Type | Default Tool | Example Use |
|------------|--------------|-------------|
| `general` | none | General LLM question |
| `math` | `calculator` | Arithmetic calculation |
| `text` | `word_count` | Text processing |
| `support` | `support_lookup` | Mock student support questions |

---

## Example Requests

The JSON responses below are from **mock mode** (`AI_PROVIDER=mock` or no API key). In that mode, `fallback_used` is `true` and answers are deterministic. In **live mode** (`AI_PROVIDER=openai` with a valid key), `fallback_used` is `false` and answers come from the configured LLM.

### 1. General Agent

```bash
curl -X POST http://127.0.0.1:8000/agent/run \
  -H "Content-Type: application/json" \
  -d '{
    "agent_type": "general",
    "query": "Who is SRK?",
    "tools": []
  }'
```

Example response in live LLM mode:

```json
{
  "status": "success",
  "agent_type": "general",
  "answer": "SRK usually refers to Shah Rukh Khan, an Indian actor, producer, and television personality.",
  "tools_used": [],
  "tool_calls": [],
  "fallback_used": false
}
```

### 2. Support Agent

```bash
curl -X POST http://127.0.0.1:8000/agent/run \
  -H "Content-Type: application/json" \
  -d '{
    "agent_type": "support",
    "query": "What is the refund policy?",
    "tools": []
  }'
```

Example response:

```json
{
  "status": "success",
  "agent_type": "support",
  "answer": "Students can request a refund within 7 days of enrollment.",
  "tools_used": ["support_lookup"],
  "tool_calls": [
    {
      "tool": "support_lookup",
      "args": {
        "query": "What is the refund policy?"
      }
    }
  ],
  "fallback_used": true
}
```

### 3. Math Agent

```bash
curl -X POST http://127.0.0.1:8000/agent/run \
  -H "Content-Type: application/json" \
  -d '{
    "agent_type": "math",
    "query": "calculate 2 + 3 * 4",
    "tools": []
  }'
```

Example response:

```json
{
  "status": "success",
  "agent_type": "math",
  "answer": "Mock math agent result: 2 + 3 * 4 = 14",
  "tools_used": ["calculator"],
  "tool_calls": [
    {
      "tool": "calculator",
      "args": {
        "expression": "2 + 3 * 4"
      }
    }
  ],
  "fallback_used": true
}
```

---

## Setup

Install dependencies using uv:

```bash
uv sync
```

Or install manually:

```bash
uv add fastapi "uvicorn[standard]" pydantic pydantic-settings python-dotenv
uv add langchain langchain-openai langchain-core
uv add --dev pytest httpx ruff
```

---

## Environment Variables

Create a `.env` file from `.env.example`.

```bash
cp .env.example .env
```

Example:

```env
APP_ENV=local
LOG_LEVEL=INFO

AI_PROVIDER=mock
OPENAI_API_KEY=

LLM_BASE_URL=
LLM_MODEL=gpt-4o-mini
LLM_TEMPERATURE=0.0
HTTP_TIMEOUT_SECONDS=15.0
```

For live OpenAI-compatible mode:

```env
AI_PROVIDER=openai
OPENAI_API_KEY=your_api_key_here
LLM_BASE_URL=https://api.groq.com/openai/v1
LLM_MODEL=openai/gpt-oss-20b
LLM_TEMPERATURE=0.0
```

Important:

- `.env` is ignored by git.
- Do not commit real API keys.
- `.env.example` is safe to commit.

---

## Run Locally

```bash
uv run uvicorn app.main:app --reload
```

Open Swagger UI:

```text
http://127.0.0.1:8000/docs
```

---

## Run Tests

```bash
uv run pytest
```

Current result:

```text
12 passed
```

---

## How Dynamic Agent Creation Works

The agent is not hardcoded as a single fixed assistant.

At runtime, the API uses request values to decide:

1. Which agent type is needed.
2. Which system prompt should be used.
3. Which tools should be attached.
4. Whether to use live LLM mode or mock fallback mode.

Example:

```json
{
  "agent_type": "math",
  "query": "calculate 2 + 3 * 4",
  "tools": []
}
```

This creates a math-focused agent and attaches the calculator tool.

---

## Mock vs Live Mode

### Mock Mode

Used when:

```env
AI_PROVIDER=mock
```

or when API key is missing.

Benefits:

- Works without API key.
- Safe for local testing.
- Deterministic responses.
- Easy to test in CI.

### Live Mode

Used when:

```env
AI_PROVIDER=openai
OPENAI_API_KEY=your_api_key_here
```

In live mode, the same API endpoint creates a real LangChain agent using the configured model.

---

## Safety Notes

- API keys are loaded from environment variables only.
- `.env` is gitignored.
- User-facing errors are returned safely.
- Internal exceptions are logged but not exposed directly.
- Mock fallback prevents the app from breaking when no key is configured.

---

## Production Improvements

Possible improvements for production:

- Authentication on `/agent/run`
- Rate limiting
- Better tool permissioning
- Request tracing and structured logging
- Conversation memory using `session_id`
- Persistent storage for agent runs
- More robust prompt-injection handling
- Deployment using Docker
- CI pipeline for tests and linting

---

## Summary

This project demonstrates a clean FastAPI API that dynamically creates a LangChain agent based on request input.

It supports both:

- local mock mode
- live OpenAI-compatible LLM mode

The implementation is intentionally small, testable, and easy to explain.
````
