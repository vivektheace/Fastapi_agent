"""API route handlers."""

import logging

from fastapi import APIRouter, HTTPException

from app import services
from app.models import RunAgentRequest, RunAgentResponse

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/agent/run", response_model=RunAgentResponse, tags=["agent"])
async def run_agent(request: RunAgentRequest) -> RunAgentResponse:
    """Accept ``agent_type``, ``query``, and optional ``tools``; run dynamic agent."""
    try:
        return await services.run_dynamic_agent(request)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Unexpected agent failure")
        raise HTTPException(status_code=500, detail="Internal server error") from exc
