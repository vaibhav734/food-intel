"""
FastAPI application factory.

Run locally:
    uvicorn food_intel.api.app:app --reload --port 8000

The app is constructed via a factory so tests can build one with overrides.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from food_intel.api.routes import analyze, health, prefill, product
from food_intel.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="Food Intelligence Platform",
        version="0.1.0",
        description=(
            "Analyzes packaged food using ingredient and nutrition data. "
            "Produces a 0–10 score with traceable, source-cited reasons. "
            "Does not provide medical advice."
        ),
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )

    app.include_router(health.router)
    app.include_router(analyze.router)
    app.include_router(prefill.router)
    app.include_router(product.router)

    return app


app = create_app()
