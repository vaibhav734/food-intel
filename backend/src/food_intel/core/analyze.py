"""
The single deterministic entry point.

`analyze(product, ruleset, catalog)` runs the full deterministic pipeline:
  product → ingredient parser → rules engine → scoring → confidence → ScoringResult

This function has zero I/O after initial config load. It does not call the
LLM, does not touch the database, does not make network requests.

Splitting the LLM-driven explanation into a separate service layer means:
  - Tests for scoring logic never need to mock an LLM
  - The same logic can be lifted into a CLI, batch job, or notebook
  - Reproducing a historical score requires only the product + rules version
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from food_intel.core import confidence as confidence_engine
from food_intel.core import scoring as scoring_engine
from food_intel.core.ingredient_parser import AdditiveCatalog, enrich_product, load_catalog
from food_intel.core.models import AgeSafety, Product, ScoringResult
from food_intel.core.rules.engine import RuleSet, evaluate


# Ingredients that are unsafe for infants under 12 months (WHO/AAP guidance)
_INFANT_RESTRICTED: frozenset[str] = frozenset([
    "honey", "salt", "added salt", "sodium", "sugar", "added sugar",
    "glucose syrup", "corn syrup", "artificial sweetener", "aspartame",
    "saccharin", "acesulfame", "sucralose",
])

# Ingredients unsafe under 36 months
_TODDLER_RESTRICTED: frozenset[str] = frozenset([
    "aspartame", "saccharin", "acesulfame", "sucralose",
    "caffeine", "alcohol",
])


def _assess_age_safety(product: Product) -> Optional[AgeSafety]:
    """Return age safety info for baby products; None for all others."""
    if product.product_type not in ("baby_food",):
        return None

    min_age = product.min_age_months
    max_age = product.max_age_months

    # Check ingredients against restricted lists
    ingredients_lower = {
        t.normalized for t in product.ingredient_tokens
    } | {i.lower().strip() for i in product.ingredients_parsed}

    unsafe_for_infant = bool(ingredients_lower & _INFANT_RESTRICTED)
    unsafe_for_toddler = bool(ingredients_lower & _TODDLER_RESTRICTED)

    # Determine effective minimum age from ingredients if not set on product
    if min_age is None:
        if unsafe_for_infant:
            min_age = 12
        elif unsafe_for_toddler:
            min_age = 36

    safe = not (unsafe_for_infant and (min_age is None or min_age < 12))

    if min_age is not None and max_age is not None:
        label = f"Suitable from {min_age} months up to {max_age} months"
    elif min_age is not None:
        label = f"Suitable from {min_age} months"
    elif max_age is not None:
        label = f"Suitable up to {max_age} months"
    else:
        label = "Age suitability unknown"

    return AgeSafety(
        min_age_months=min_age,
        max_age_months=max_age,
        label=label,
        safe=safe,
    )


def analyze(
    product: Product,
    ruleset: RuleSet,
    catalog: Optional[AdditiveCatalog] = None,
) -> ScoringResult:
    """
    Run the deterministic pipeline.

    If `catalog` is provided and the product has raw ingredients, the parser
    runs first to populate ingredient_tokens and flagged_additive_classes.
    Skipping the catalog (or omitting raw ingredients) is fine — the rules
    engine handles missing data gracefully.
    """
    if catalog is not None and product.ingredients_raw:
        enrich_product(product, catalog)

    hits = evaluate(product, ruleset)
    final_score, raw_score, verdict = scoring_engine.score(
        hits, ruleset.verdict_bands
    )
    confidence_level, completeness, missing = confidence_engine.assess(product)

    # Apply confidence cap: a product with missing critical data cannot claim
    # a high score. This prevents false positives like "10/10 with no data".
    cap = ruleset.confidence_caps.get(confidence_level.value, 10)
    was_capped = final_score > cap
    if was_capped:
        final_score = cap
        verdict = scoring_engine.derive_verdict(final_score, ruleset.verdict_bands)

    # data_unavailable: score is meaningless — no rules fired AND score was capped.
    # This means we have no real signal, just a default penalised by missing data.
    data_unavailable = was_capped and len(hits) == 0

    return ScoringResult(
        score=final_score,
        raw_score=round(raw_score, 3),
        verdict=verdict,
        reasons=hits,
        confidence=confidence_level,
        completeness=completeness,
        missing_fields=missing,
        rules_version=ruleset.version,
        age_safety=_assess_age_safety(product),
        data_unavailable=data_unavailable,
    )


# ---------------------------------------------------------------------------
# Convenience loader for callers who want defaults
# ---------------------------------------------------------------------------

_CONFIG_DIR = Path(__file__).parent / "rules" / "config"


def load_default_config() -> tuple[RuleSet, AdditiveCatalog]:
    """Load the bundled v1 ruleset + additives catalog."""
    from food_intel.core.rules.engine import load_ruleset
    ruleset = load_ruleset(_CONFIG_DIR / "rules_v1.yaml")
    catalog = load_catalog(_CONFIG_DIR / "additives_v1.yaml")
    return ruleset, catalog


def load_cosmetics_config() -> tuple[RuleSet, AdditiveCatalog]:
    """Load the cosmetics ruleset + cosmetics ingredients catalog."""
    from food_intel.core.rules.engine import load_ruleset
    ruleset = load_ruleset(_CONFIG_DIR / "cosmetics_v1.yaml")
    catalog = load_catalog(_CONFIG_DIR / "cosmetics_ingredients_v1.yaml")
    return ruleset, catalog


def load_baby_food_config() -> tuple[RuleSet, AdditiveCatalog]:
    """Load the baby food ruleset (reuses the standard additives catalog)."""
    from food_intel.core.rules.engine import load_ruleset
    ruleset = load_ruleset(_CONFIG_DIR / "baby_food_v1.yaml")
    catalog = load_catalog(_CONFIG_DIR / "additives_v1.yaml")
    return ruleset, catalog
