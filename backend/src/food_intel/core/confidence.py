"""
Confidence engine.

Confidence reflects how much we trust the score given the input data.
A high confidence means the product had nearly all required fields populated;
low means we scored it with significant gaps.

Crucially, low confidence does NOT suppress the score — the API still returns
a number, just with a flag the UI can surface. Hiding scores on partial data
makes the system feel broken; showing them with a caveat is honest.
"""

from __future__ import annotations

from food_intel.core.models import Confidence, Product


# Field weights sum to 1.0. Tune these by importance to the score, not by
# how often they're missing — sugar is more weighted than serving_size
# because the score depends on it more.
FIELD_WEIGHTS: dict[str, float] = {
    "sugar_g": 0.25,
    "saturated_fat_g": 0.20,
    "sodium_mg": 0.20,
    "protein_g": 0.15,
    "serving_size_g": 0.10,
    "ingredients_raw": 0.10,
}

# For cosmetics and baby_food-cosmetic hybrids, confidence is based solely
# on ingredients presence — nutrition fields are not applicable.
COSMETIC_FIELD_WEIGHTS: dict[str, float] = {
    "ingredients_raw": 1.0,
}

HIGH_THRESHOLD: float = 0.85
MEDIUM_THRESHOLD: float = 0.55


def assess(product: Product) -> tuple[Confidence, float, list[str]]:
    """
    Returns (confidence_level, completeness_fraction, missing_field_names).

    For cosmetics, confidence is based solely on ingredients presence.
    For food/baby_food, it uses the full nutrition field weights.
    """
    weights = COSMETIC_FIELD_WEIGHTS if product.product_type == "cosmetic" else FIELD_WEIGHTS
    completeness = 0.0
    missing: list[str] = []

    for field_name, weight in weights.items():
        if _is_present(product, field_name):
            completeness += weight
        else:
            missing.append(field_name)

    if completeness >= HIGH_THRESHOLD:
        level = Confidence.HIGH
    elif completeness >= MEDIUM_THRESHOLD:
        level = Confidence.MEDIUM
    else:
        level = Confidence.LOW

    return level, round(completeness, 3), missing


def _is_present(product: Product, field_name: str) -> bool:
    """A field counts as present if non-None and (for strings/lists) non-empty."""
    # Ingredients live on the Product, nutrition fields on product.nutrition
    if field_name == "ingredients_raw":
        value = product.ingredients_raw
    else:
        value = getattr(product.nutrition, field_name, None)

    if value is None:
        return False
    if isinstance(value, str) and not value.strip():
        return False
    return True
