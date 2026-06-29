from __future__ import annotations

from typing import AsyncIterator

from app.schemas.llm import LlmMessage, StreamDone, TextDelta, ToolCallDelta, ToolSpec, Usage


class LLMProvider:
    """Abstract base — the only surface the orchestrator sees."""

    name: str = "base"
    model: str = "none"

    async def stream(
        self,
        *,
        system: str,
        messages: list[LlmMessage],
        tools: list[ToolSpec],
    ) -> AsyncIterator[TextDelta | ToolCallDelta | Usage | StreamDone]:
        raise NotImplementedError
        yield  # make it a typed async generator
