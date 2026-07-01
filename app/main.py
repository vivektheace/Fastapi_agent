"""FastAPI application entry point."""

import logging

from fastapi import FastAPI

from app.config import get_settings
from app.routes import router


def configure_logging() -> None:
    settings = get_settings()
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


configure_logging()

app = FastAPI(
    title="FastAPI LangChain Dynamic Agent API",
    version="0.1.0",
    description=(
        "Creates a LangChain agent dynamically per request based on agent_type "
        "and optional tools. Uses the configured LLM when a key is present, "
        "otherwise a mock fallback."
    ),
)

app.include_router(router)


@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    """Return service health status."""
    return {"status": "ok"}
