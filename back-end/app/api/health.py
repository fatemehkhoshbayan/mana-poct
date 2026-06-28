from __future__ import annotations

from fastapi import APIRouter

from app.schemas.api import HealthResponse

router = APIRouter(tags=["health"])


@router.get(
    "/api/health",
    response_model=HealthResponse,
    summary="Health check",
    description="Returns `{status: ok}` when the backend is up.",
)
async def health() -> HealthResponse:
    return HealthResponse(status="ok")
