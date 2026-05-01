"""Tests for baby food and cosmetics scoring paths, and data_unavailable flag."""

from __future__ import annotations

import pytest

from food_intel.core import analyze, load_baby_food_config, load_cosmetics_config
from food_intel.core.models import NutritionFacts, Product, Verdict


@pytest.fixture(scope="module")
def baby_ruleset():
    ruleset, _ = load_baby_food_config()
    return ruleset


@pytest.fixture(scope="module")
def cosmetics_ruleset():
    ruleset, _ = load_cosmetics_config()
    return ruleset


@pytest.fixture(scope="module")
def baby_catalog():
    _, catalog = load_baby_food_config()
    return catalog


@pytest.fixture(scope="module")
def cosmetics_catalog():
    _, catalog = load_cosmetics_config()
    return catalog


# ---------------------------------------------------------------------------
# Baby food
# ---------------------------------------------------------------------------

class TestBabyFoodHighSugar:
    """Bournvita-like product — 73g sugar per 100g should score very low."""

    def test_scores_low(self, baby_ruleset, baby_catalog):
        product = Product(
            name="Bournvita",
            product_type="baby_food",
            nutrition=NutritionFacts(
                sugar_g=73.0, saturated_fat_g=1.5, sodium_mg=200,
                protein_g=7.5, fiber_g=1.2, serving_size_g=20,
            ),
        )
        result = analyze(product, baby_ruleset, baby_catalog)
        assert result.score <= 3
        assert result.verdict == Verdict.LIMIT

    def test_sugar_high_rule_fires(self, baby_ruleset, baby_catalog):
        product = Product(
            name="High Sugar Baby Food",
            product_type="baby_food",
            nutrition=NutritionFacts(sugar_g=73.0, saturated_fat_g=1.5,
                                     sodium_mg=200, protein_g=7.5,
                                     fiber_g=1.2, serving_size_g=20),
        )
        result = analyze(product, baby_ruleset, baby_catalog)
        rule_ids = {h.rule_id for h in result.reasons}
        assert "baby_sugar_high" in rule_ids

    def test_not_data_unavailable(self, baby_ruleset, baby_catalog):
        product = Product(
            name="Full Data Baby Food",
            product_type="baby_food",
            nutrition=NutritionFacts(sugar_g=73.0, saturated_fat_g=1.5,
                                     sodium_mg=200, protein_g=7.5,
                                     fiber_g=1.2, serving_size_g=20),
        )
        result = analyze(product, baby_ruleset, baby_catalog)
        assert result.data_unavailable is False


class TestBabyFoodClean:
    """Clean baby food — low sugar, low sodium, no additives."""

    def test_scores_high(self, baby_ruleset, baby_catalog):
        product = Product(
            name="Clean Baby Puree",
            product_type="baby_food",
            nutrition=NutritionFacts(
                sugar_g=2.0, saturated_fat_g=0.5, sodium_mg=30,
                protein_g=6.0, fiber_g=1.5, serving_size_g=100,
            ),
        )
        result = analyze(product, baby_ruleset, baby_catalog)
        assert result.score >= 7


# ---------------------------------------------------------------------------
# Cosmetics
# ---------------------------------------------------------------------------

class TestCosmeticsWithParabens:
    def test_scores_below_midpoint(self, cosmetics_ruleset, cosmetics_catalog):
        product = Product(
            name="Face Cream",
            product_type="cosmetic",
            ingredients_raw="Water, Glycerin, Methylparaben, Propylparaben, Fragrance",
            flagged_additive_classes=["paraben", "synthetic_fragrance"],
        )
        result = analyze(product, cosmetics_ruleset, cosmetics_catalog)
        assert result.score <= 6
        assert result.verdict in (Verdict.MODERATE, Verdict.LIMIT)

    def test_paraben_rule_fires(self, cosmetics_ruleset, cosmetics_catalog):
        product = Product(
            name="Face Cream",
            product_type="cosmetic",
            flagged_additive_classes=["paraben"],
        )
        result = analyze(product, cosmetics_ruleset, cosmetics_catalog)
        rule_ids = {h.rule_id for h in result.reasons}
        assert "cosmetic_parabens" in rule_ids


class TestCosmeticsClean:
    def test_clean_cosmetic_scores_high(self, cosmetics_ruleset, cosmetics_catalog):
        product = Product(
            name="Natural Moisturiser",
            product_type="cosmetic",
            ingredients_raw="Water, Aloe Vera, Shea Butter, COSMOS Organic",
            flagged_additive_classes=["certified_organic"],
        )
        result = analyze(product, cosmetics_ruleset, cosmetics_catalog)
        assert result.score >= 7


# ---------------------------------------------------------------------------
# data_unavailable flag
# ---------------------------------------------------------------------------

class TestDataUnavailable:
    def test_no_data_sets_flag(self, baby_ruleset):
        """Product with zero nutrition data and low confidence → data_unavailable."""
        product = Product(name="Empty", product_type="baby_food",
                          nutrition=NutritionFacts())
        result = analyze(product, baby_ruleset)
        assert result.data_unavailable is True

    def test_partial_data_does_not_set_flag(self, baby_ruleset):
        """If at least one rule fires, data_unavailable must be False."""
        product = Product(
            name="Partial",
            product_type="baby_food",
            nutrition=NutritionFacts(sugar_g=50.0),  # sugar_high fires
        )
        result = analyze(product, baby_ruleset)
        assert result.data_unavailable is False

    def test_food_no_data_sets_flag(self, ruleset):
        product = Product(name="Mystery", nutrition=NutritionFacts())
        result = analyze(product, ruleset)
        assert result.data_unavailable is True
