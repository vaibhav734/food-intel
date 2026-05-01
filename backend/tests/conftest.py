"""Shared test fixtures, including the three worked-example products."""

from __future__ import annotations

from pathlib import Path

import pytest

from food_intel.core import NutritionFacts, Product, load_ruleset
from food_intel.core.rules.engine import RuleSet


RULES_PATH = (
    Path(__file__).parent.parent
    / "src"
    / "food_intel"
    / "core"
    / "rules"
    / "config"
    / "rules_v1.yaml"
)


@pytest.fixture(scope="session")
def ruleset() -> RuleSet:
    """The v1 ruleset — loaded once per test session."""
    return load_ruleset(RULES_PATH)


@pytest.fixture
def oats() -> Product:
    """Plain rolled oats — should score near the top."""
    return Product(
        name="Plain Rolled Oats",
        nutrition=NutritionFacts(
            calories_kcal=379,
            sugar_g=1.0,
            saturated_fat_g=1.2,
            sodium_mg=5,
            protein_g=13.0,
            fiber_g=10.0,
            serving_size_g=40,
        ),
        ingredients_raw="100% rolled oats",
        ingredients_parsed=["rolled oats"],
        flagged_additive_classes=[],
        nova_class=1,
    )


@pytest.fixture
def cereal() -> Product:
    """Typical sugary breakfast cereal — should land mid-range."""
    return Product(
        name="Sugar-Frosted Corn Cereal",
        nutrition=NutritionFacts(
            calories_kcal=380,
            sugar_g=25.0,
            saturated_fat_g=2.0,
            sodium_mg=450,
            protein_g=7.0,
            fiber_g=4.0,
            serving_size_g=30,
        ),
        ingredients_raw="corn, sugar, glucose syrup, salt, flavoring, color (E160a), BHT",
        ingredients_parsed=["corn", "sugar", "glucose syrup", "salt"],
        flagged_additive_classes=["color", "antioxidant"],
        nova_class=4,
    )


@pytest.fixture
def noodles() -> Product:
    """Instant noodles — should score low."""
    return Product(
        name="Instant Noodles, Spicy",
        nutrition=NutritionFacts(
            calories_kcal=450,
            sugar_g=3.0,
            saturated_fat_g=7.0,
            sodium_mg=1400,
            protein_g=4.0,
            fiber_g=1.0,
            serving_size_g=85,
        ),
        ingredients_raw="wheat flour, palm oil, salt, MSG, flavor enhancer (E621), color (E150d)",
        ingredients_parsed=["wheat flour", "palm oil", "salt"],
        flagged_additive_classes=["flavor enhancer", "color", "stabilizer"],
        nova_class=4,
    )


@pytest.fixture
def sparse_product() -> Product:
    """Product with most fields missing — exercises low-confidence path."""
    return Product(
        name="Mystery Snack",
        nutrition=NutritionFacts(sugar_g=15.0),
    )
