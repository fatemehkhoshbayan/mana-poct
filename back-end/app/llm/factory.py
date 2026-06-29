from __future__ import annotations

from app.config import settings
from app.llm.base import LLMProvider


def get_provider() -> LLMProvider:
    """Return OpenRouterProvider when a key is set, else FakeProvider."""
    if settings.has_llm_key:
        from app.llm.openrouter_provider import OpenRouterProvider  # noqa: PLC0415

        return OpenRouterProvider(model=settings.LLM_MODEL)

    from app.llm.fake import FakeProvider  # noqa: PLC0415

    return FakeProvider()
