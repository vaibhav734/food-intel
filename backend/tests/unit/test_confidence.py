"""Unit tests for the confidence engine."""

from __future__ import annotations

import pytest

from food_intel.core.confidence import FIELD_WEIGHTS, assess
from food_intel.core.models import Confidence, NutritionFacts, Product


def test_field_weights_sum_to_one():
    """Sanity check: completeness can never exceed 1.0."""
    assert abs(sum(FIELD_WEIGHTS.values()) - 1.0) < 1e-9


def test_full_data_is_high_confidence(oats):
    level, completeness, missing = assess(oats)
    assert level == Confidence.HIGH
    assert completeness == 1.0
    assert missing == []


def test_no_data_is_low_confidence():
    product = Product(name="empty", nutrition=NutritionFacts())
    level, completeness, missing = assess(product)
    assert level == Confidence.LOW
    assert completeness == 0.0
    assert set(missing) == set(FIELD_WEIGHTS.keys())


def test_partial_data_lands_in_medium_band():
    # Populate ~60% by weight: sugar (.25) + sat_fat (.20) + sodium (.20) = .65
    product = Product(
        name="partial",
        nutrition=NutritionFacts(sugar_g=10, saturated_fat_g=2, sodium_mg=300),
    )
    level, completeness, missing = assess(product)
    assert level == Confidence.MEDIUM
    assert completeness == pytest.approx(0.65)
    assert "protein_g" in missing
    assert "ingredients_raw" in missing


def test_empty_string_ingredients_counted_missing():
    """Ingredients_raw="" should not count as present."""
    product = Product(
        name="test",
        nutrition=NutritionFacts(
            sugar_g=5, saturated_fat_g=2, sodium_mg=100,
            protein_g=5, serving_size_g=30,
        ),
        ingredients_raw="   ",  # whitespace only
    )
    _, _, missing = assess(product)
    assert "ingredients_raw" in missing


def test_sparse_product_fixture(sparse_product):
    """The fixture has only sugar_g — should be low confidence."""
    level, completeness, _ = assess(sparse_product)
    assert level == Confidence.LOW
    assert completeness == FIELD_WEIGHTS["sugar_g"]
