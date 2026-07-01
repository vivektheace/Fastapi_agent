"""Service layer: orchestrates dynamic agent creation and execution."""

import logging

from app.agent import (
    create_dynamic_agent,
    extract_final_answer,
    extract_tool_calls,
    resolve_tool_names,
    run_mock_agent,
)
from app.config import get_settings
from app.models import RunAgentRequest, RunAgentResponse

logger = logging.getLogger(__name__)


async def run_dynamic_agent(request: RunAgentRequest) -> RunAgentResponse:
    """Run a dynamically created agent and return a structured response.

    Flow:
    1. Validate query.
    2. Select prompt + tools from ``agent_type`` and optional ``tools``.
    3. Use live LangChain agent when a key is configured, else mock fallback.
    4. Shape the result into ``RunAgentResponse``.
    """
    settings = get_settings()
    tools_used = resolve_tool_names(request.agent_type, request.tools)

    if settings.ai_provider.lower() == "mock" or not settings.openai_api_key:
        logger.warning("Using mock fallback agent agent_type=%s", request.agent_type)
        return await run_mock_agent(request)

    try:
        agent = create_dynamic_agent(request, settings=settings)
        result = await agent.ainvoke(
            {"messages": [{"role": "user", "content": request.query}]}
        )

        answer = extract_final_answer(result)
        tool_calls = extract_tool_calls(result)

        if not answer:
            return RunAgentResponse(
                status="fallback",
                agent_type=request.agent_type,
                answer="I could not generate a confident answer.",
                tools_used=tools_used,
                tool_calls=tool_calls,
                fallback_used=True,
            )

        return RunAgentResponse(
            status="success",
            agent_type=request.agent_type,
            answer=answer,
            tools_used=tools_used,
            tool_calls=tool_calls,
            fallback_used=False,
        )

    except Exception:
        logger.exception("LangChain agent execution failed")
        return RunAgentResponse(
            status="fallback",
            agent_type=request.agent_type,
            answer="Agent execution failed. Please try again.",
            tools_used=tools_used,
            tool_calls=[],
            fallback_used=True,
        )
