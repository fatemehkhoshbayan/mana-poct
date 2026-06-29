"""Per-turn orchestration loop: FSM objective → LLM stream → tool execution → decision."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date
from typing import Any, AsyncIterator

from app.domain.rules_engine import resolve
from app.llm.base import LLMProvider
from app.orchestration.fsm import all_known, mark_known, next_objective
from app.orchestration.prompts import build_system_prompt
from app.orchestration.tools import ALL_TOOLS, execute_tool
from app.schemas.domain import Decision, ExtractionState, FsmState
from app.schemas.llm import LlmMessage, StreamDone, TextDelta, ToolCall, ToolCallDelta

logger = logging.getLogger(__name__)

MAX_TOOL_ITERATIONS = 4


@dataclass
class TokenEvent:
    text: str


@dataclass
class StateEvent:
    extraction: ExtractionState
    current_state: FsmState
    current_objective: str


@dataclass
class DecisionEvent:
    decision: Decision


@dataclass
class ErrorEvent:
    message: str


OrchestratorEvent = TokenEvent | StateEvent | DecisionEvent | ErrorEvent


class Orchestrator:
    def __init__(self, provider: LLMProvider) -> None:
        self._provider = provider

    async def handle_turn(
        self,
        session_id: str,
        tenant_id: str,
        history: list[LlmMessage],
        user_message: str,
        extraction: ExtractionState,
        today: date | None = None,
    ) -> AsyncIterator[OrchestratorEvent]:
        """
        Process one user turn. Yields OrchestratorEvents:
          - TokenEvent     per LLM text chunk
          - StateEvent     after each tool execution
          - DecisionEvent  when all 4 variables are resolved
          - ErrorEvent     on recoverable failure
        """
        if today is None:
            today = date.today()

        # Append the user message to history
        messages = list(history) + [LlmMessage(role="user", content=user_message)]

        # Re-derive known flags from current extraction state
        extraction = mark_known(extraction, today)

        logger.info(
            "handle_turn session=%s  provider=%s  known=[c=%s s=%s h=%s e=%s]",
            session_id,
            self._provider.name,
            extraction.consumable_known,
            extraction.storage_known,
            extraction.historical_known,
            extraction.eqa_known,
        )

        for _iteration in range(MAX_TOOL_ITERATIONS):
            objective = next_objective(extraction)
            system_prompt = build_system_prompt(objective)

            logger.info(
                "  iteration=%d  objective=%s  history_len=%d",
                _iteration,
                objective.value,
                len(messages),
            )

            accumulated_text = ""
            pending_tool_calls: list[ToolCall] = []

            async for event in self._provider.stream(
                system=system_prompt,
                messages=messages,
                tools=ALL_TOOLS,
            ):
                if isinstance(event, TextDelta):
                    accumulated_text += event.text
                    yield TokenEvent(text=event.text)

                elif isinstance(event, ToolCallDelta):
                    pending_tool_calls.append(event.call)

                elif isinstance(event, StreamDone):
                    break

            logger.info(
                "  stream done: text_len=%d  tool_calls=%s",
                len(accumulated_text),
                [tc.name for tc in pending_tool_calls],
            )

            # Append assistant turn to history
            messages.append(
                LlmMessage(
                    role="assistant",
                    content=accumulated_text,
                    tool_calls=pending_tool_calls,
                )
            )

            if not pending_tool_calls:
                # No tool calls — turn ends; await more input from operator
                logger.info("  no tool calls — turn ends")
                break

            # Execute tool calls and append results
            for tc in pending_tool_calls:
                extraction, result_json = execute_tool(
                    tc.name, tc.arguments, extraction
                )
                messages.append(
                    LlmMessage(
                        role="tool",
                        content=result_json,
                        tool_call_id=tc.id,
                        name=tc.name,
                    )
                )

            # Emit state update after tool execution
            objective = next_objective(extraction)
            logger.info(
                "  after tools: known=[c=%s s=%s h=%s e=%s]  next_obj=%s",
                extraction.consumable_known,
                extraction.storage_known,
                extraction.historical_known,
                extraction.eqa_known,
                objective.value,
            )
            yield StateEvent(
                extraction=extraction,
                current_state=objective,
                current_objective=objective.value,
            )

            # If all variables known, resolve
            if all_known(extraction):
                break

        # Final check: if all variables are now known, compute decision
        if all_known(extraction):
            logger.info("  all known — invoking rules engine")
            try:
                decision = resolve(
                    extraction,
                    session_id=session_id,
                    tenant_id=tenant_id,
                    today=today,
                )
                logger.info(
                    "  decision: scenario=%s  consumable=%s  storage=%s  historical=%s  eqa=%s",
                    decision.scenario.value,
                    decision.variables.get("consumable_status"),
                    decision.variables.get("storage_condition"),
                    decision.variables.get("historical_error_flag"),
                    decision.variables.get("eqa_status"),
                )
                yield DecisionEvent(decision=decision)
            except Exception as exc:
                logger.exception("Rules engine failed")
                yield ErrorEvent(message=f"Decision engine error: {exc}")

    def updated_messages(
        self,
        history: list[LlmMessage],
        user_message: str,
        assistant_text: str,
        tool_calls: list[Any] | None = None,
    ) -> list[LlmMessage]:
        """Convenience: build the updated message list after a turn."""
        msgs = list(history)
        msgs.append(LlmMessage(role="user", content=user_message))
        msgs.append(
            LlmMessage(
                role="assistant", content=assistant_text, tool_calls=tool_calls or []
            )
        )
        return msgs
