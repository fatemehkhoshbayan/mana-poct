from __future__ import annotations

import json
import logging
import re
from typing import AsyncIterator

from openai import AsyncOpenAI

from app.config import settings
from app.llm.base import LLMProvider
from app.llm.translate import messages_to_wire, tools_to_wire
from app.schemas.llm import (
    LlmMessage,
    StreamDone,
    TextDelta,
    ToolCall,
    ToolCallDelta,
    ToolSpec,
    Usage,
)

logger = logging.getLogger(__name__)

# Claude extended-thinking tokens that leak into the text stream via OpenRouter
_THINKING_RE = re.compile(r"<\|channel\>.*?<channel\|>", re.DOTALL)


def _strip_thinking(text: str) -> str:
    """Remove any chain-of-thought thinking markers that bleed into streamed text."""
    return _THINKING_RE.sub("", text)


class OpenRouterProvider(LLMProvider):
    name = "openrouter"

    def __init__(self, model: str) -> None:
        self.model = model
        self._client = AsyncOpenAI(
            base_url=settings.OPENROUTER_BASE_URL,
            api_key=settings.OPENROUTER_API_KEY,
            default_headers={
                "HTTP-Referer": settings.OPENROUTER_HTTP_REFERER or "",
                "X-Title": settings.OPENROUTER_APP_TITLE or "MANA POCT QC Assistant",
            },
        )

    async def stream(
        self,
        *,
        system: str,
        messages: list[LlmMessage],
        tools: list[ToolSpec],
    ) -> AsyncIterator[TextDelta | ToolCallDelta | Usage | StreamDone]:
        wire_messages = messages_to_wire(system, messages)
        wire_tools = tools_to_wire(tools) if tools else []

        kwargs: dict = {
            "model": self.model,
            "messages": wire_messages,
            "stream": True,
            "extra_body": {"usage": {"include": True}},
        }
        if wire_tools:
            kwargs["tools"] = wire_tools

        stream = await self._client.chat.completions.create(**kwargs)

        # Index-based tool-call accumulator
        acc: dict[int, dict] = {}

        async for chunk in stream:
            if not chunk.choices:
                # Final usage-bearing chunk (OpenRouter specific)
                if chunk.usage:
                    yield Usage(
                        input_tokens=chunk.usage.prompt_tokens,
                        output_tokens=chunk.usage.completion_tokens,
                    )
                continue

            delta = chunk.choices[0].delta

            if delta.content:
                text = _strip_thinking(delta.content)
                if text:
                    yield TextDelta(text=text)

            for tc in delta.tool_calls or []:
                slot = acc.setdefault(tc.index, {"id": "", "name": "", "args": ""})
                if tc.id:
                    slot["id"] = tc.id
                if tc.function and tc.function.name:
                    slot["name"] = tc.function.name
                if tc.function and tc.function.arguments:
                    slot["args"] += tc.function.arguments

        # Emit fully-accumulated tool calls
        for slot in acc.values():
            try:
                args = json.loads(slot["args"] or "{}")
            except json.JSONDecodeError:
                args = {}
            yield ToolCallDelta(call=ToolCall(id=slot["id"], name=slot["name"], arguments=args))

        yield StreamDone()
