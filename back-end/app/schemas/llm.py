from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Literal


@dataclass
class LlmMessage:
    role: Literal["system", "user", "assistant", "tool"]
    content: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)
    tool_call_id: str | None = None
    name: str | None = None


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class ToolSpec:
    name: str
    description: str
    parameters: dict[str, Any]


@dataclass
class TextDelta:
    text: str


@dataclass
class ToolCallDelta:
    call: ToolCall


@dataclass
class Usage:
    input_tokens: int
    output_tokens: int


@dataclass
class StreamDone:
    pass


StreamEvent = "TextDelta | ToolCallDelta | Usage | StreamDone"


class LLMProvider:
    """The only surface the orchestrator sees. Implementations live in app/llm/."""

    name: str
    model: str

    async def stream(
        self,
        *,
        system: str,
        messages: list[LlmMessage],
        tools: list[ToolSpec],
    ) -> AsyncIterator[TextDelta | ToolCallDelta | Usage | StreamDone]:
        raise NotImplementedError
        yield  # make it an async generator
