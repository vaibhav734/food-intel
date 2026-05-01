"""Public surface of the deterministic core."""

from food_intel.core.analyze import analyze, load_baby_food_config, load_cosmetics_config, load_default_config
from food_intel.core.ingredient_parser import (
    AdditiveCatalog,
    enrich_product,
    load_catalog,
    parse,
)
from food_intel.core.models import (
    Confidence,
    IngredientToken,
    NutritionFacts,
    Product,
    RuleHit,
    ScoringResult,
    Source,
    SourceType,
    Verdict,
)
from food_intel.core.rules.engine import RuleSet, load_ruleset

__all__ = [
    "AdditiveCatalog",
    "Confidence",
    "IngredientToken",
    "NutritionFacts",
    "Product",
    "RuleHit",
    "RuleSet",
    "ScoringResult",
    "Source",
    "SourceType",
    "Verdict",
    "analyze",
    "enrich_product",
    "load_baby_food_config",
    "load_catalog",
    "load_cosmetics_config",
    "load_default_config",
    "load_ruleset",
    "parse",
]
