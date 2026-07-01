"""Dynamic LangChain agent factory.

Builds an agent at runtime from ``agent_type``, optional ``tools``, and
configuration. Provides a deterministic mock path when no LLM key is available.
"""

import logging
import re
from typing import Any

from langchain.agents import create_agent
from langchain_core.tools import BaseTool, tool

from app.config import Settings, get_settings
from app.models import RunAgentRequest, RunAgentResponse, ToolCallTrace

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Demo tools (registered by name for dynamic selection)
# ---------------------------------------------------------------------------


@tool
def calculator(expression: str) -> str:
    """Evaluate a simple math expression such as ``2 + 3 * 4``."""
    allowed = set("0123456789+-*/(). ")
    if not expression or not set(expression).issubset(allowed):
        return "Invalid mathematical expression."
    try:
        return str(eval(expression, {"__builtins__": {}}, {}))
    except Exception:
        return "Unable to calculate the expression."


@tool
def word_count(text: str) -> str:
    """Return the number of words in the given text."""
    if not text.strip():
        return "0"
    return str(len(text.split()))


@tool
def support_lookup(query: str) -> str:
    """Look up mock student-support policies (refund, course, payment)."""
    lower = query.lower()
    if "refund" in lower:
        return "Students can request a refund within 7 days of enrollment."
    if "course" in lower:
        return "Course details are available in the student dashboard."
    if "payment" in lower:
        return "Payment issues should be checked in the billing section."
    return "No exact support policy found for this query."


TOOL_REGISTRY: dict[str, BaseTool] = {
    "calculator": calculator,
    "word_count": word_count,
    "support_lookup": support_lookup,
}

DEFAULT_TOOLS_BY_TYPE: dict[str, list[str]] = {
    "general": [],
    "math": ["calculator"],
    "text": ["word_count"],
    "support": ["support_lookup"],
}

SYSTEM_PROMPTS: dict[str, str] = {
    "general": (
        "You are a helpful general assistant. Answer clearly and concisely using "
        "the provided tools when they help."
    ),
    "math": (
        "You are a math assistant. Use the calculator tool whenever a calculation "
        "is needed."
    ),
    "text": (
        "You are a text-processing assistant. Use word_count when the user asks "
        "about word counts or text analysis."
    ),
    "support": (
        "You are a student support assistant. Use support_lookup for course, "
        "refund, payment, or enrollment questions."
    ),
}


# ---------------------------------------------------------------------------
# Deterministic auto-router (keyword + simple regex, no LLM call)
# ---------------------------------------------------------------------------

MATH_KEYWORDS = (
    "calculate", "compute", "add", "sum", "subtract", "minus", "multiply",
    "divide", "division", "percentage", "percent", "average",
)
SUPPORT_KEYWORDS = (
    "refund", "enrollment", "enroll", "course", "payment", "fee", "fees",
    "login", "password", "support", "student", "certificate", "class", "issue",
)
TEXT_KEYWORDS = (
    "word count", "count words", "count the words", "number of words",
    "character count", "count characters", "count the characters",
)

_ARITHMETIC_PATTERN = re.compile(r"\d\s*[+\-*/]\s*\d")
_TEXT_PATTERN = re.compile(r"count\b.*\b(words?|characters?)")


def infer_agent_type(query: str) -> str:
    """Infer an agent type from the query using simple deterministic rules.

    Priority order: math, then support, then text, then general. This is a
    keyword/regex router (no external LLM call) so routing stays explainable.
    """
    lower = query.lower()

    if _ARITHMETIC_PATTERN.search(lower) or any(word in lower for word in MATH_KEYWORDS):
        return "math"

    if any(word in lower for word in SUPPORT_KEYWORDS):
        return "support"

    if _TEXT_PATTERN.search(lower) or any(word in lower for word in TEXT_KEYWORDS):
        return "text"

    return "general"


def get_system_prompt(agent_type: str) -> str:
    """Return the system prompt for the requested agent type."""
    return SYSTEM_PROMPTS.get(agent_type, SYSTEM_PROMPTS["general"])


def resolve_tool_names(agent_type: str, requested_tools: list[str]) -> list[str]:
    """Merge default tools for ``agent_type`` with optional request tools."""
    seen: set[str] = set()
    ordered: list[str] = []
    for name in [*DEFAULT_TOOLS_BY_TYPE.get(agent_type, []), *requested_tools]:
        if name in TOOL_REGISTRY and name not in seen:
            seen.add(name)
            ordered.append(name)
    return ordered


def get_tools(agent_type: str, requested_tools: list[str]) -> list[BaseTool]:
    """Return LangChain tool instances selected for this request."""
    return [TOOL_REGISTRY[name] for name in resolve_tool_names(agent_type, requested_tools)]


def _build_chat_model(settings: Settings) -> Any:
    """Create the configured chat model (OpenAI or compatible endpoint)."""
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured")

    from langchain_openai import ChatOpenAI

    extra: dict[str, Any] = {}
    if settings.llm_base_url:
        extra["base_url"] = settings.llm_base_url

    return ChatOpenAI(
        model=settings.llm_model,
        temperature=settings.llm_temperature,
        api_key=settings.openai_api_key,
        timeout=settings.http_timeout_seconds,
        **extra,
    )


def create_dynamic_agent(
    request: RunAgentRequest,
    settings: Settings | None = None,
    model: Any | None = None,
) -> Any:
    """Build a LangChain agent dynamically for this request.

    Args:
        request: Incoming API request (agent_type, query, tools).
        settings: Optional settings override (tests).
        model: Optional pre-built chat model (tests).

    Returns:
        A compiled LangChain agent graph with ``ainvoke``.
    """
    settings = settings or get_settings()
    tools = get_tools(request.agent_type, request.tools)
    system_prompt = get_system_prompt(request.agent_type)
    chat_model = model or _build_chat_model(settings)

    logger.info(
        "Creating dynamic agent agent_type=%s tools=%s",
        request.agent_type,
        [t.name for t in tools],
    )

    return create_agent(
        model=chat_model,
        tools=tools,
        system_prompt=system_prompt,
    )


def extract_final_answer(result: Any) -> str:
    """Extract the last non-empty AI message from an agent result."""
    if not isinstance(result, dict):
        return ""

    for message in reversed(result.get("messages", [])):
        content = getattr(message, "content", None)
        if isinstance(content, str) and content.strip():
            return content.strip()
    return ""


def extract_tool_calls(result: Any) -> list[ToolCallTrace]:
    """Collect tool-call traces from an agent result."""
    if not isinstance(result, dict):
        return []

    traces: list[ToolCallTrace] = []
    for message in result.get("messages", []):
        calls = getattr(message, "tool_calls", None)
        if not calls:
            continue
        for call in calls:
            traces.append(
                ToolCallTrace(
                    tool=call.get("name", "unknown"),
                    args=call.get("args", {}) or {},
                )
            )
    return traces


def _extract_math_expression(query: str) -> str | None:
    """Pull a simple arithmetic expression out of a user query."""
    matches = re.findall(r"\d[\d+\-*/().\s]*", query)

    if not matches:
        return None

    expr = max(matches, key=len).strip()
    allowed = set("0123456789+-*/(). ")

    if expr and set(expr).issubset(allowed):
        return expr

    return None


async def run_mock_agent(request: RunAgentRequest) -> RunAgentResponse:
    """Deterministic fallback when no LLM key is configured.

    Still respects ``agent_type`` and selected tools so the API stays testable
    without calling an external model provider.
    """
    query = request.query.strip()
    tool_names = resolve_tool_names(request.agent_type, request.tools)
    tool_calls: list[ToolCallTrace] = []

    if request.agent_type == "math" and "calculator" in tool_names:
        expr = _extract_math_expression(query) or "2 + 2"
        result = calculator.invoke({"expression": expr})
        tool_calls.append(ToolCallTrace(tool="calculator", args={"expression": expr}))
        answer = f"Mock math agent result: {expr} = {result}"
    elif request.agent_type == "text" and "word_count" in tool_names:
        result = word_count.invoke({"text": query})
        tool_calls.append(ToolCallTrace(tool="word_count", args={"text": query}))
        answer = f"Mock text agent result: the query contains {result} words."
    elif request.agent_type == "support" and "support_lookup" in tool_names:
        result = support_lookup.invoke({"query": query})
        tool_calls.append(ToolCallTrace(tool="support_lookup", args={"query": query}))
        answer = result
    else:
        answer = (
            f"Mock agent (type={request.agent_type}) processed your query: "
            f"'{query}'. Set OPENAI_API_KEY and AI_PROVIDER=openai for live mode."
        )

    return RunAgentResponse(
        status="success",
        agent_type=request.agent_type,
        answer=answer,
        tools_used=tool_names,
        tool_calls=tool_calls,
        fallback_used=True,
    )
