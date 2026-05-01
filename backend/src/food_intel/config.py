"""
Application settings.

Loaded from environment variables (with .env support via pydantic-settings).
Centralized here so the rest of the app never reads os.environ directly.
"""

from __future__ import annotations

from typing import Literal

try:
    from pydantic_settings import BaseSettings, SettingsConfigDict
except ImportError:  # pragma: no cover — optional API dependency
    BaseSettings = object  # type: ignore[assignment,misc]
    SettingsConfigDict = dict  # type: ignore[assignment,misc]


class Settings(BaseSettings):
    """API + provider configuration."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="FOOD_INTEL_",
        extra="ignore",
    )

    # LLM provider selection
    llm_provider: Literal["null", "anthropic", "openai"] = "null"
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-haiku-4-5-20251001"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"

    # Product lookup
    enable_openfoodfacts: bool = True
    usda_api_key: str = ""
    product_db_path: str = ""  # override SQLite DB path; empty = auto-detect

    # CORS
    cors_origins: str = "http://localhost:5173"  # vite dev server default

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


def get_settings() -> Settings:
    """Factory used by the dependency injection layer."""
    return Settings()
