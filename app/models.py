"""Pydantic request/response schemas for the agent API."""

from pydantic import BaseModel, Field, field_validator


class RunAgentRequest(BaseModel):
    """Request body for ``POST /agent/run``."""

    agent_type: str = Field(
        default="general",
        description="Agent personality that selects the default prompt and tools.",
        examples=["general", "math", "text", "support"],
    )
    query: str = Field(
        ...,
        min_length=1,
        description="Natural-language question for the agent.",
    )
    tools: list[str] = Field(
        default_factory=list,
        description="Optional extra tool names to attach to the agent at runtime.",
    )

    @field_validator("query")
    @classmethod
    def strip_and_validate_query(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Query cannot be empty")
        return stripped


class ToolCallTrace(BaseModel):
    """Record of one tool invocation during an agent run."""

    tool: str
    args: dict = Field(default_factory=dict)


class RunAgentResponse(BaseModel):
    """Structured response from ``POST /agent/run``."""

    status: str
    agent_type: str
    answer: str
    tools_used: list[str] = Field(default_factory=list)
    tool_calls: list[ToolCallTrace] = Field(default_factory=list)
    fallback_used: bool = False
