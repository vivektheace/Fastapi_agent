---
name: python-dev
description: "Python development guidance with code quality standards, error handling, testing practices, environment management, and AI-assisted code review. Use when writing, reviewing, or modifying Python code (.py files) or Jupyter notebooks (.ipynb files)."
---

# Python Development Skill

## Overview

Use this skill for Python backend, API, automation, data processing, AI application code, and Jupyter notebooks.

The goal is to write Python code that is:
- readable
- type-safe
- testable
- easy to debug
- easy to explain
- safe to run in production-like environments

Use AI tools to accelerate coding, but always manually review generated code for correctness, simplicity, security, and maintainability.

---

## When to Use This Skill

Use this skill when:
- Writing new Python code
- Modifying existing Python files
- Creating or updating Jupyter notebooks
- Building backend APIs
- Writing AI/LLM service functions
- Creating tests
- Reviewing AI-generated Python code
- Setting up Python development environments

---

## Code Quality Principles

- Prefer simple solutions over clever ones.
- Keep functions small and focused on one responsibility.
- Avoid code duplication.
- Use composition and helper functions before complex inheritance.
- Prefer pure functions when possible.
- Build the common use case first, then handle edge cases.
- Make the code easy to explain to another developer.
- Avoid unnecessary abstraction during early implementation.
- Keep business logic separate from framework-specific code.

---

## Naming, Typing, and Documentation

- Use `snake_case` for variables, functions, and modules.
- Use clear and meaningful names.
- Add type hints for function parameters and return values.
- Use Pydantic models or dataclasses for structured data.
- Use Google-style docstrings for important functions, classes, and modules.
- Keep comments short and useful.
- Preserve existing comments unless they are wrong or outdated.

### Example

```python
def calculate_total(items: list[dict[str, float]], tax_rate: float = 0.08) -> float:
    """Calculate total cost including tax.

    Args:
        items: List of items with a 'price' key.
        tax_rate: Tax rate as decimal.

    Returns:
        Total cost including tax.

    Raises:
        ValueError: If items is empty or tax_rate is negative.
    """
    if not items:
        raise ValueError("Items list cannot be empty")
    if tax_rate < 0:
        raise ValueError("Tax rate cannot be negative")

    subtotal = sum(item["price"] for item in items)
    return subtotal * (1 + tax_rate)
```

---

## Error Handling

- Validate inputs early at the function boundary.
- Catch specific exception types, not bare `except`.
- Do not silently swallow errors.
- Raise clear errors with useful messages.
- Do not expose secrets, tokens, or internal stack traces in user-facing errors.
- Add fallback logic only when it is meaningful and safe.
- Log unexpected failures before returning a generic error response.

### Example

```python
from pathlib import Path


def process_file(file_path: str) -> list[str]:
    """Read a text file and return non-empty stripped lines.

    Args:
        file_path: Path to the file.

    Returns:
        List of non-empty lines.

    Raises:
        ValueError: If file_path is empty.
        FileNotFoundError: If file does not exist.
        PermissionError: If file cannot be read.
    """
    if not file_path:
        raise ValueError("File path cannot be empty")

    path = Path(file_path)

    try:
        with path.open("r", encoding="utf-8") as file:
            return [line.strip() for line in file if line.strip()]
    except FileNotFoundError as exc:
        raise FileNotFoundError(f"File not found: {file_path}") from exc
    except PermissionError as exc:
        raise PermissionError(f"Permission denied: {file_path}") from exc
```

---

## Efficiency Patterns

- Use f-strings for string formatting.
- Use list/dict/set comprehensions when they improve readability.
- Use context managers with `with` for files, connections, locks, and resources.
- Use dictionaries for lookup-heavy logic.
- Use sets for uniqueness checks.
- Avoid unnecessary nested loops when a hashmap/set can solve the problem.
- Avoid repeated string concatenation inside large loops; use list append and `"".join(...)`.
- Avoid loading large files fully into memory when streaming is possible.
- Avoid repeated external API calls in loops when batching is possible.

---

## AI-Generated Code Review Checklist

When using Cursor, Copilot, Claude, ChatGPT, or similar tools:

1. Check all imports.
2. Check function signatures.
3. Check whether the code actually matches the requirement.
4. Check input validation.
5. Check edge cases.
6. Check response format.
7. Check error handling.
8. Remove unnecessary code.
9. Simplify over-engineered output.
10. Ensure no fake package, fake API, or imaginary method is used.
11. Make sure the code runs locally.
12. Test at least one happy path and one failure path.

AI can generate boilerplate quickly, but final correctness is the developer's responsibility.

---

## Testing

### Framework and Structure

- Prefer `pytest` for Python testing.
- Put tests in a `tests/` directory.
- Add `__init__.py` in `tests/` when package discovery needs it.
- Write or update tests for new/modified service-layer logic.
- Test critical endpoints and business functions.
- All tests should pass before considering the task complete.

### Test Cases to Cover

- Happy path
- Empty input
- Invalid input
- Missing required fields
- Boundary values
- External service failure
- AI/LLM empty response or malformed response

### Example Test

```python
import pytest

from src.calculations import calculate_total


def test_calculate_total_basic() -> None:
    """Test basic total calculation."""
    items = [{"price": 10.0}, {"price": 20.0}]

    result = calculate_total(items, tax_rate=0.1)

    assert result == 33.0


def test_calculate_total_empty_list() -> None:
    """Test error handling for empty list."""
    with pytest.raises(ValueError, match="Items list cannot be empty"):
        calculate_total([])


def test_calculate_total_negative_tax() -> None:
    """Test error handling for negative tax rate."""
    items = [{"price": 10.0}]

    with pytest.raises(ValueError, match="Tax rate cannot be negative"):
        calculate_total(items, tax_rate=-0.1)
```

---

## Environment Management

### Preferred Setup

Prefer `uv` for dependency management when available.

Use:
```bash
uv init
uv add fastapi uvicorn pydantic python-dotenv pytest ruff
uv run python app/main.py
uv run pytest
```

### Fallback Setup

If `uv` is not available in the working environment, use standard Python virtual environment commands:

```bash
python -m venv .venv
source .venv/bin/activate
pip install fastapi uvicorn pydantic python-dotenv pytest ruff
pip freeze > requirements.txt
```

On Windows:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install fastapi uvicorn pydantic python-dotenv pytest ruff
pip freeze > requirements.txt
```

Do not block implementation only because the preferred package manager is unavailable.

---

## Linting and Formatting

Prefer Ruff for linting and formatting.

```bash
uv run ruff check .
uv run ruff check --fix .
uv run ruff format .
```

Fallback:

```bash
ruff check .
ruff check --fix .
ruff format .
```

---

## Type Checking

Use Pyright when available.

```bash
uv run pyright
```

Fallback:

```bash
pyright
```

For quick POCs, type hints are still expected, but full strict type-checking can be mentioned as a production improvement if time is limited.

---

## Best Practices Summary

1. Code quality: simple, readable, DRY, small functions.
2. Style: type hints, snake_case, useful docstrings.
3. Errors: early validation, specific exceptions, no bare except.
4. Efficiency: f-strings, comprehensions, context managers, hashmap/set where useful.
5. Testing: pytest, happy path, edge cases, failures.
6. Environment: prefer uv, fallback to venv/pip when needed.
7. Linting: Ruff.
8. Type checking: Pyright when available.
9. AI code: use tools for speed, but manually verify everything.
