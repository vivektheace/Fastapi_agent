---
name: fastapi-api-dev
description: "FastAPI backend API development workflow. Use when creating, reviewing, or modifying Python FastAPI applications, API endpoints, request/response schemas, service layers, AI/LLM endpoints, file upload APIs, tests, and API documentation."
---

# FastAPI API Development Skill

## Overview

Use this skill to build clean, modular, testable FastAPI applications.

The goal is to convert requirements into a working API with:

- clear API contract
- Pydantic request and response models
- thin route handlers
- service-layer business logic
- validation and error handling
- practical logging hooks
- basic tests
- concise documentation

Use AI tools to accelerate boilerplate, but manually review architecture, code, edge cases, and final behavior.

---

## When to Use This Skill

Use this skill when:

- Creating a new FastAPI application
- Adding or modifying API endpoints
- Building backend services for AI/LLM workflows
- Creating file upload APIs
- Adding Pydantic models
- Refactoring route logic into services
- Writing FastAPI tests
- Creating API usage examples

---

## Development Workflow

1. Understand the requirement.
2. Identify input, output, and expected behavior.
3. Convert the requirement into an API contract.
4. Define request and response schemas.
5. Define route names and HTTP methods.
6. Define service-layer functions.
7. Identify validations and edge cases.
8. Implement the smallest correct version.
9. Add safe error handling and useful logging hooks.
10. Test one happy path and one failure path.

Follow project rules for security, environment configuration, logging, testing, and README documentation.

---

## API Contract First

For every new endpoint, define:

- endpoint path
- HTTP method
- request body
- response body
- status codes
- validation rules
- error cases
- service function name

### Example API Contract

```text
Endpoint: POST /classify
Purpose: Classify a user message into a category.

Request:
{
  "text": "I need help with my course payment"
}

Response:
{
  "status": "success",
  "category": "billing",
  "confidence": 0.86,
  "reason": "The message talks about payment."
}

Errors:
- 400: empty text
- 500: classification service failure
```

---

## Recommended Project Structure

Prefer this structure for small to medium FastAPI services:

```text
project/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── models.py
│   ├── routes.py
│   ├── services.py
│   └── config.py
├── tests/
│   ├── __init__.py
│   ├── test_routes.py
│   └── test_services.py
├── .env.example
├── .gitignore
├── README.md
└── pyproject.toml or requirements.txt
```

For very small apps, it is acceptable to start with fewer files, but keep route logic and business logic separate when the project grows.

---

## FastAPI App Setup

Create a simple app entry point.

```python
from fastapi import FastAPI

from app.routes import router

app = FastAPI(
    title="FastAPI Service",
    version="1.0.0",
    description="Backend API service",
)

app.include_router(router)


@app.get("/health")
def health() -> dict[str, str]:
    """Return service health status."""
    return {"status": "ok"}
```

---

## Pydantic Models

Use Pydantic models for request validation and response structure.

```python
from pydantic import BaseModel, Field


class ClassifyRequest(BaseModel):
    text: str = Field(..., min_length=1, description="Input text to classify")


class ClassifyResponse(BaseModel):
    status: str
    category: str
    confidence: float
    reason: str
```

Guidelines:

- Keep request and response models explicit.
- Use meaningful model names.
- Add validation for required fields.
- Avoid returning inconsistent response shapes.
- Prefer structured JSON over free-form strings.

---

## Thin Routes, Service Layer Logic

Routes should handle HTTP concerns. Business logic should stay in service functions.

### Route Layer

```python
import logging

from fastapi import APIRouter, HTTPException

from app.models import ClassifyRequest, ClassifyResponse
from app.services import classify_text

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/classify", response_model=ClassifyResponse)
def classify(request: ClassifyRequest) -> ClassifyResponse:
    """Classify input text."""
    try:
        logger.info("Classification request received")
        return classify_text(request.text)
    except ValueError as exc:
        logger.warning("Invalid classification request: %s", exc)
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Unexpected classification failure")
        raise HTTPException(status_code=500, detail="Internal server error") from exc
```

### Service Layer

```python
from app.models import ClassifyResponse


def classify_text(text: str) -> ClassifyResponse:
    """Classify text into a simple category."""
    cleaned_text = text.strip()

    if not cleaned_text:
        raise ValueError("Text cannot be empty")

    lower_text = cleaned_text.lower()

    if "payment" in lower_text or "invoice" in lower_text:
        category = "billing"
        confidence = 0.86
        reason = "The message contains payment-related terms."
    else:
        category = "general"
        confidence = 0.65
        reason = "No specific category matched strongly."

    return ClassifyResponse(
        status="success",
        category=category,
        confidence=confidence,
        reason=reason,
    )
```

---

## Error Handling

Use clear and safe error handling.

- Use `HTTPException` for API-facing errors.
- Use `400` for invalid input.
- Use `404` for missing resources.
- Use `500` for unexpected server errors.
- Do not expose internal stack traces to API users.
- Log unexpected failures internally.
- Use safe error messages in responses.

Common pattern:

```python
try:
    result = service_function()
except ValueError as exc:
    raise HTTPException(status_code=400, detail=str(exc)) from exc
except Exception as exc:
    logger.exception("Unexpected error")
    raise HTTPException(status_code=500, detail="Internal server error") from exc
```

---

## External API Calls

When calling external APIs or LLM providers:

- use timeout
- handle network failure
- handle invalid response
- avoid infinite retries
- do not call expensive APIs repeatedly inside loops
- keep the provider call inside a service function

Example:

```python
import httpx


def call_external_api(url: str, payload: dict) -> dict:
    """Call external API with timeout."""
    try:
        response = httpx.post(url, json=payload, timeout=20)
        response.raise_for_status()
        return response.json()
    except httpx.TimeoutException as exc:
        raise RuntimeError("External API timeout") from exc
    except httpx.HTTPError as exc:
        raise RuntimeError("External API request failed") from exc
```

---

## AI / LLM Endpoint Pattern

For AI endpoints, keep the flow explicit:

```text
Request
→ validate input
→ build prompt or messages
→ call model/service
→ validate model output
→ apply fallback if needed
→ return structured response
```

Guidelines:

- Keep prompts outside route handlers.
- Keep model calls inside service functions.
- Return structured JSON.
- Validate model output before returning it.
- Add fallback for empty or malformed responses.
- Track prompt name/version when useful.
- Avoid exposing hidden/system prompts.

### Example AI Response Shape

```json
{
  "status": "success",
  "answer": "The answer text",
  "confidence": 0.82,
  "fallback_used": false,
  "sources": []
}
```

---

## File Upload APIs

When implementing file upload:

- use `UploadFile`
- validate file type
- validate file size
- avoid trusting user-provided filenames
- handle empty files
- handle unsupported files
- avoid loading very large files fully into memory

Example:

```python
from fastapi import APIRouter, File, HTTPException, UploadFile

router = APIRouter()


@router.post("/upload")
async def upload_file(file: UploadFile = File(...)) -> dict[str, str]:
    """Upload a file for processing."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required")

    allowed_extensions = {".txt", ".pdf", ".md"}

    if not any(file.filename.lower().endswith(ext) for ext in allowed_extensions):
        raise HTTPException(status_code=400, detail="Unsupported file type")

    return {"status": "success", "filename": file.filename}
```

---

## FastAPI Testing

Use `pytest` and `TestClient` for API endpoint tests.

```python
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
```

Test:

- `/health`
- main happy path
- missing fields
- empty strings
- invalid types
- expected response shape
- service failure/fallback when relevant

---

## Completion Checklist

Before considering the API complete:

1. Requirement is converted into API contract.
2. Request and response models are clear.
3. Route handler is thin.
4. Business logic is in service layer.
5. Input validation exists.
6. Errors are handled safely.
7. Logs are added for important steps.
8. `/health` endpoint exists.
9. Main endpoint runs locally.
10. Happy path tested.
11. One failure path tested.
12. No secrets are hardcoded.

---

## Best Practices Summary

1. Contract first, code second.
2. Pydantic for schemas.
3. Thin routes, service layer for logic.
4. Structured JSON responses.
5. Safe error handling.
6. Practical logging.
7. Environment variables for config.
8. Basic tests with pytest/TestClient.
9. Keep API behavior easy to run, test, and explain.
10. AI tools accelerate code, but developer owns correctness.
