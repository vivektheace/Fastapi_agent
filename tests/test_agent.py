"""Tests for the dynamic agent API."""

import asyncio

import pytest
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage, HumanMessage

from app import services
from app.agent import (
    create_dynamic_agent,
    get_tools,
    infer_agent_type,
    resolve_tool_names,
    run_mock_agent,
)
from app.config import Settings
from app.models import RunAgentRequest


class FakeAgent:
    """Stand-in for a compiled LangChain agent."""

    def __init__(self, messages: list) -> None:
        self._messages = messages

    async def ainvoke(self, payload: dict) -> dict:
        return {"messages": self._messages}


def test_health(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_resolve_tools_by_agent_type() -> None:
    assert resolve_tool_names("math", []) == ["calculator"]
    assert resolve_tool_names("text", []) == ["word_count"]
    assert resolve_tool_names("support", []) == ["support_lookup"]
    assert resolve_tool_names("general", []) == []


def test_resolve_tools_with_optional_request_tools() -> None:
    names = resolve_tool_names("general", ["calculator", "unknown_tool"])
    assert names == ["calculator"]


def test_get_tools_returns_langchain_tools() -> None:
    tools = get_tools("math", [])
    assert len(tools) == 1
    assert tools[0].name == "calculator"


def test_mock_agent_support() -> None:
    request = RunAgentRequest(agent_type="support", query="How do I get a refund?")
    response = asyncio.run(run_mock_agent(request))

    assert response.fallback_used is True
    assert "refund" in response.answer.lower()
    assert "support_lookup" in response.tools_used
    assert response.tool_calls[0].tool == "support_lookup"


def test_mock_agent_text() -> None:
    request = RunAgentRequest(agent_type="text", query="hello world test")
    response = asyncio.run(run_mock_agent(request))

    assert response.fallback_used is True
    assert "3 words" in response.answer


def test_infer_agent_type_rules() -> None:
    assert infer_agent_type("calculate 2 + 3 * 4") == "math"
    assert infer_agent_type("what is 20 percent of 500") == "math"
    assert infer_agent_type("What is the refund policy?") == "support"
    assert infer_agent_type("Count the words in this sentence: hello world") == "text"
    assert infer_agent_type("Who is Shah Rukh Khan?") == "general"


def _auto_route(monkeypatch, query: str, agent_type: str | None = None):
    monkeypatch.setenv("OPENAI_API_KEY", "")
    monkeypatch.setenv("AI_PROVIDER", "mock")
    from app.config import get_settings

    get_settings.cache_clear()

    kwargs = {"query": query}
    if agent_type is not None:
        kwargs["agent_type"] = agent_type
    request = RunAgentRequest(**kwargs)
    return asyncio.run(services.run_dynamic_agent(request))


def test_auto_route_math(monkeypatch) -> None:
    response = _auto_route(monkeypatch, "calculate 2 + 3 * 4")
    assert response.agent_type == "math"
    assert "calculator" in response.tools_used


def test_auto_route_support(monkeypatch) -> None:
    response = _auto_route(monkeypatch, "What is the refund policy?")
    assert response.agent_type == "support"
    assert "support_lookup" in response.tools_used


def test_auto_route_text(monkeypatch) -> None:
    response = _auto_route(
        monkeypatch, "Count the words in this sentence: FastAPI creates APIs quickly"
    )
    assert response.agent_type == "text"
    assert "word_count" in response.tools_used


def test_auto_route_general(monkeypatch) -> None:
    response = _auto_route(monkeypatch, "Who is Shah Rukh Khan?")
    assert response.agent_type == "general"


def test_explicit_agent_type_overrides_auto(monkeypatch) -> None:
    response = _auto_route(monkeypatch, "calculate 2 + 3", agent_type="general")
    assert response.agent_type == "general"
    assert response.tools_used == []


def test_run_dynamic_agent_uses_mock_without_key(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "")
    monkeypatch.setenv("AI_PROVIDER", "mock")
    from app.config import get_settings

    get_settings.cache_clear()

    request = RunAgentRequest(agent_type="support", query="refund policy")
    response = asyncio.run(services.run_dynamic_agent(request))

    assert response.fallback_used is True
    assert response.agent_type == "support"


def test_run_dynamic_agent_live_path(monkeypatch) -> None:
    messages = [
        HumanMessage(content="What is 2+2?"),
        AIMessage(content="The answer is 4."),
    ]

    def fake_create(request, settings=None, model=None):
        return FakeAgent(messages)

    monkeypatch.setattr("app.services.create_dynamic_agent", fake_create)
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("AI_PROVIDER", "openai")
    from app.config import get_settings

    get_settings.cache_clear()

    request = RunAgentRequest(agent_type="math", query="What is 2+2?")
    response = asyncio.run(services.run_dynamic_agent(request))

    assert response.status == "success"
    assert response.fallback_used is False
    assert "4" in response.answer
    assert "calculator" in response.tools_used


def test_agent_run_route(client: TestClient, monkeypatch) -> None:
    async def fake_run(request: RunAgentRequest):
        from app.models import RunAgentResponse

        return RunAgentResponse(
            status="success",
            agent_type=request.agent_type,
            answer="ok",
            tools_used=["calculator"],
            fallback_used=False,
        )

    monkeypatch.setattr(services, "run_dynamic_agent", fake_run)

    response = client.post(
        "/agent/run",
        json={
            "agent_type": "math",
            "query": "2 + 2",
            "tools": ["calculator"],
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["agent_type"] == "math"
    assert body["tools_used"] == ["calculator"]


def test_agent_run_route_empty_query(client: TestClient) -> None:
    response = client.post("/agent/run", json={"agent_type": "general", "query": ""})
    assert response.status_code == 422


def test_agent_run_route_whitespace_query(client: TestClient) -> None:
    response = client.post("/agent/run", json={"agent_type": "general", "query": "   "})
    assert response.status_code == 422


def test_create_dynamic_agent_requires_key() -> None:
    settings = Settings(openai_api_key="")
    request = RunAgentRequest(agent_type="math", query="1+1")

    with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
        create_dynamic_agent(request, settings=settings)
