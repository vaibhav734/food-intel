"""
Dependency injection wiring.

Builds the AnalysisService from settings + the bundled config files.
Concrete adapters (LLM provider, product lookup) are picked here.

The functions are wrapped in @lru_cache so the same service instance is
reused across requests — important because loading the rules YAML and
constructing LLM clients is non-trivial work.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Optional

from fastapi import Depends

from food_intel.adapters.llm.anthropic_provider import AnthropicExplanationProvider
from food_intel.adapters.llm.base import ExplanationProvider
from food_intel.adapters.llm.null_provider import NullExplanationProvider
from food_intel.adapters.llm.openai_provider import OpenAIExplanationProvider
from food_intel.adapters.product_lookup.base import ProductLookup
from food_intel.adapters.product_lookup.multi_source import MultiSourceLookup
from food_intel.config import Settings, get_settings
from food_intel.core import load_default_config
from food_intel.services.analyze import AnalysisService


@lru_cache(maxsize=1)
def _cached_settings() -> Settings:
    return get_settings()


@lru_cache(maxsize=1)
def _cached_core_config():
    return load_default_config()  # (ruleset, catalog)


def get_explanation_provider(
    settings: Settings = Depends(_cached_settings),
) -> ExplanationProvider:
    """Pick the LLM provider based on settings."""
    if settings.llm_provider == "anthropic" and settings.anthropic_api_key:
        return AnthropicExplanationProvider(
            api_key=settings.anthropic_api_key,
            model=settings.anthropic_model,
        )
    if settings.llm_provider == "openai" and settings.openai_api_key:
        return OpenAIExplanationProvider(
            api_key=settings.openai_api_key,
            model=settings.openai_model,
        )
    return NullExplanationProvider()


def get_product_lookup(
    settings: Settings = Depends(_cached_settings),
) -> Optional[ProductLookup]:
    """Pick the product lookup adapter (or None if disabled)."""
    if settings.enable_openfoodfacts:
        db_path = Path(settings.product_db_path) if settings.product_db_path else None
        db_url = settings.product_db_url or None
        return MultiSourceLookup(
            usda_api_key=settings.usda_api_key or None,
            db_path=db_path,
            db_url=db_url,
        )
    return None


def get_analysis_service(
    settings: Settings = Depends(_cached_settings),
    explanation_provider: ExplanationProvider = Depends(get_explanation_provider),
    product_lookup: Optional[ProductLookup] = Depends(get_product_lookup),
) -> AnalysisService:
    """Build the AnalysisService — the entry point used by routes."""
    ruleset, catalog = _cached_core_config()
    return AnalysisService(
        ruleset=ruleset,
        catalog=catalog,
        explanation_provider=explanation_provider,
        product_lookup=product_lookup,
    )
