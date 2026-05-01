"""Health check endpoints for liveness and readiness probes."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    """Liveness — is the process up?"""
    return {"status": "ok"}


@router.get("/ready")
def ready() -> dict[str, str]:
    """
    Readiness — can we actually serve requests?

    Right now this is identical to /health because the core has no external
    dependencies that need to be reachable. When we add a database, this
    endpoint should verify connection.
    """
    return {"status": "ready"}
