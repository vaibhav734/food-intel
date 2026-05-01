"""
Core domain models.

These are the data shapes that flow through the deterministic core. They are
deliberately decoupled from:
  - the database schema (SQLAlchemy models live in adapters/persistence)
  - the API contract (request/response schemas live in api/schemas.py)

Keeping these separate lets each layer evolve at its own pace.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class Confidence(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Verdict(str, Enum):
    EXCELLENT = "Excellent"
    GOOD = "Good"
    MODERATE = "Moderate"
    LIMIT = "Limit"


class SourceType(str, Enum):
    GUIDELINE = "guideline"        # external standard (WHO, FDA, etc.)
    LABEL_DERIVED = "label-derived" # taken directly from product label
    COMPUTED = "computed"           # derived by our engine


@dataclass(frozen=True)
class Source:
    """Where a piece of evidence comes from. Every rule hit carries one."""
    org: str                        # "WHO", "FDA", "USDA", "ICMR", etc.
    type: SourceType
    doc: Optional[str] = None       # human-readable citation


@dataclass
class NutritionFacts:
    """
    Per-100g nutrition values. Always normalized to per-100g before reaching
    the rules engine — see core/normalization.py for per-serving conversion.

    Any field may be None; the confidence engine handles partial data.
    """
    calories_kcal: Optional[float] = None
    sugar_g: Optional[float] = None
    saturated_fat_g: Optional[float] = None
    sodium_mg: Optional[float] = None
    protein_g: Optional[float] = None
    fiber_g: Optional[float] = None
    serving_size_g: Optional[float] = None  # kept for confidence scoring


@dataclass
class IngredientToken:
    """
    A single ingredient extracted from the raw label string.

    Categories are non-exclusive — the same token can be both a "sugar" and
    "added_sugars". `additive_class` is set only for E-numbers and named
    additives (those drive the additives_flagged rule).
    """
    text: str                       # original ingredient string
    normalized: str                 # lowercased, whitespace-collapsed
    e_number: Optional[int] = None  # 100..999 if detected
    additive_class: Optional[str] = None
    categories: list[str] = field(default_factory=list)


@dataclass
class Product:
    """A normalized product, ready for scoring."""
    name: str
    barcode: Optional[str] = None
    nutrition: NutritionFacts = field(default_factory=NutritionFacts)
    ingredients_raw: Optional[str] = None      # the printed ingredient list
    ingredients_parsed: list[str] = field(default_factory=list)
    ingredient_tokens: list[IngredientToken] = field(default_factory=list)
    flagged_additive_classes: list[str] = field(default_factory=list)
    nova_class: Optional[int] = None           # 1..4 if known
    product_type: str = "food"                 # "food", "baby_food", "cosmetic"
    # Age safety: populated for baby products. None means no age restriction known.
    min_age_months: Optional[int] = None       # e.g. 6 means "from 6 months"
    max_age_months: Optional[int] = None       # e.g. 36 means "up to 3 years"


@dataclass(frozen=True)
class RuleHit:
    """
    The result of a single rule firing against a product. This is the atomic
    unit of explainability — every score component is a list of these.
    """
    rule_id: str
    text: str                       # human-readable reason
    delta: float                    # signed contribution to score (-2.5, +1.0, ...)
    source: Source
    observed_value: Optional[float] = None
    threshold: Optional[float] = None


@dataclass
class AgeSafety:
    """Age-range suitability for baby/child products."""
    min_age_months: Optional[int]   # None = no lower bound known
    max_age_months: Optional[int]   # None = no upper bound
    label: str                      # e.g. "Suitable from 6 months"
    safe: bool                      # False if product contains restricted ingredients for age


@dataclass
class ScoringResult:
    """The full output of the deterministic pipeline. The LLM only sees this."""
    score: int                      # 0..10, integer for display
    raw_score: float                # pre-clamp, pre-round, for debugging
    verdict: Verdict
    reasons: list[RuleHit]
    confidence: Confidence
    completeness: float             # 0..1, weighted data completeness
    missing_fields: list[str]
    rules_version: str              # which rules YAML produced this
    age_safety: Optional[AgeSafety] = None  # populated for baby products
    data_unavailable: bool = False  # True when score is meaningless due to missing data
