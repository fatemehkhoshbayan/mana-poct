"""Throwaway hello-stream endpoint — proves the SSE pipeline end-to-end (Slice 0).
Delete after Slice 1 is wired.
"""

from __future__ import annotations

import asyncio

from fastapi import APIRouter
from sse_starlette import EventSourceResponse

router = APIRouter(tags=["hello"])

_TOKENS = ["QC ", "assistant ", "online", ".", ""]


@router.post(
    "/api/hello/stream",
    summary="[Slice 0] Hello stream — proves SSE pipeline",
    description=(
        "Streams 5 hardcoded `token` events then a `done` event. "
        "This endpoint is a Slice-0 smoke test and will be removed after Slice 1."
    ),
)
async def hello_stream() -> EventSourceResponse:
    async def gen():
        try:
            for tok in _TOKENS:
                await asyncio.sleep(0.15)
                yield {"event": "token", "data": tok}
            yield {"event": "done", "data": "[DONE]"}
        except GeneratorExit:
            return

    return EventSourceResponse(gen(), headers={"X-Accel-Buffering": "no"})
