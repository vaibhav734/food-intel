"""
Analysis service.

This is the orchestration seam — it wires together the core (deterministic),
the product lookup adapter, and the LLM adapter. The API layer calls into
this service; it never reaches into the core directly.

If you ever build a CLI, a batch job, or a Slack bot, they all call into
this same service.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from food_intel.adapters.llm.base import ExplanationProvider
from food_intel.adapters.product_lookup.base import ProductLookup, ProductNotFoundError
from food_intel.core import (
    AdditiveCatalog,
    Product,
    RuleSet,
    ScoringResult,
    analyze,
    load_baby_food_config,
    load_cosmetics_config,
    load_default_config,
)


@dataclass
class AnalysisResult:
    """The full output: deterministic score + LLM-generated explanation."""
    product: Product
    scoring: ScoringResult
    explanation: str


class AnalysisService:
    """Service-layer entry point for the analyze workflow."""

    def __init__(
        self,
        ruleset: RuleSet,
        catalog: AdditiveCatalog,
        explanation_provider: ExplanationProvider,
        product_lookup: Optional[ProductLookup] = None,
    ):
        self.ruleset = ruleset
        self.catalog = catalog
        self.explanation_provider = explanation_provider
        self.product_lookup = product_lookup
        # Alternate rulesets loaded lazily on first use
        self._cosmetics_ruleset: Optional[RuleSet] = None
        self._cosmetics_catalog: Optional[AdditiveCatalog] = None
        self._baby_ruleset: Optional[RuleSet] = None
        self._baby_catalog: Optional[AdditiveCatalog] = None

    def _get_ruleset_and_catalog(self, product: Product) -> tuple[RuleSet, AdditiveCatalog]:
        if product.product_type == "cosmetic":
            if self._cosmetics_ruleset is None:
                self._cosmetics_ruleset, self._cosmetics_catalog = load_cosmetics_config()
            return self._cosmetics_ruleset, self._cosmetics_catalog
        if product.product_type == "baby_food":
            if not hasattr(self, "_baby_ruleset") or self._baby_ruleset is None:
                self._baby_ruleset, self._baby_catalog = load_baby_food_config()
            return self._baby_ruleset, self._baby_catalog
        return self.ruleset, self.catalog

    def analyze_product(self, product: Product) -> AnalysisResult:
        """Run the full pipeline on an already-constructed Product."""
        ruleset, catalog = self._get_ruleset_and_catalog(product)
        scoring = analyze(product, ruleset, catalog)
        explanation = self.explanation_provider.generate_explanation(product, scoring)
        return AnalysisResult(product=product, scoring=scoring, explanation=explanation)

    def analyze_by_barcode(self, barcode: str) -> AnalysisResult:
        """Look up the product by barcode, then analyze it."""
        if self.product_lookup is None:
            raise RuntimeError(
                "No product_lookup configured; cannot analyze by barcode."
            )
        product = self.product_lookup.get_by_barcode(barcode)
        if product is None:
            raise ProductNotFoundError(f"No product found for barcode {barcode}")
        return self.analyze_product(product)
