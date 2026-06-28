"""Sessions API — Surface F.

Slice 0: stub returning a placeholder (real implementation in Slice 1).
"""
from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(tags=["sessions"])

# Slice 1 will add POST /api/sessions, POST /api/sessions/{id}/messages,
# and GET /api/sessions/{id} fully wired to the orchestrator + DB.
