"""Translate between normalized LlmMessage/ToolSpec and the OpenAI Chat Completions
wire format, which OpenRouter also speaks.
"""

from __future__ import annotations

from typing import Any

from app.schemas.llm import LlmMessage, ToolSpec


def messages_to_wire(system: str, messages: list[LlmMessage]) -> list[dict[str, Any]]:
    wire: list[dict[str, Any]] = [{"role": "system", "content": system}]
    for m in messages:
        if m.role == "tool":
            wire.append(
                {
                    "role": "tool",
                    "tool_call_id": m.tool_call_id,
                    "content": m.content,
                }
            )
        elif m.role == "assistant" and m.tool_calls:
            wire.append(
                {
                    "role": "assistant",
                    "content": m.content or None,
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.name,
                                "arguments": _dump_args(tc.arguments),
                            },
                        }
                        for tc in m.tool_calls
                    ],
                }
            )
        else:
            wire.append({"role": m.role, "content": m.content})
    return wire


def tools_to_wire(tools: list[ToolSpec]) -> list[dict[str, Any]]:
    return [
        {
            "type": "function",
            "function": {
                "name": t.name,
                "description": t.description,
                "parameters": t.parameters,
            },
        }
        for t in tools
    ]


def _dump_args(arguments: dict[str, Any]) -> str:
    import json

    return json.dumps(arguments)
