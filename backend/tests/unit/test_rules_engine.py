"""Unit tests for the rules engine."""

from __future__ import annotations

from food_intel.core.models import NutritionFacts, Product
from food_intel.core.rules.engine import (
    _check_numeric_condition,
    _interpolated_delta,
    evaluate,
)


# --------------------------------------------------------------------------
# Condition primitives
# --------------------------------------------------------------------------


class TestNumericConditions:
    def test_gt(self):
        assert _check_numeric_condition(10, {"gt": 5}) is True
        assert _check_numeric_condition(5, {"gt": 5}) is False

    def test_gte(self):
        assert _check_numeric_condition(5, {"gte": 5}) is True
        assert _check_numeric_condition(4.99, {"gte": 5}) is False

    def test_lt(self):
        assert _check_numeric_condition(3, {"lt": 5}) is True
        assert _check_numeric_condition(5, {"lt": 5}) is False

    def test_between_is_half_open(self):
        # [lo, hi) — lo inclusive, hi exclusive
        assert _check_numeric_condition(5, {"between": [5, 10]}) is True
        assert _check_numeric_condition(7.5, {"between": [5, 10]}) is True
        assert _check_numeric_condition(10, {"between": [5, 10]}) is False
        assert _check_numeric_condition(4.99, {"between": [5, 10]}) is False


# --------------------------------------------------------------------------
# Interpolation
# --------------------------------------------------------------------------


class TestInterpolation:
    def test_at_lower_bound_returns_zero(self):
        assert _interpolated_delta(5.0, -1.0, {"from": 5.0, "to": 22.5}) == 0.0

    def test_at_upper_bound_returns_full_delta(self):
        assert _interpolated_delta(22.5, -1.0, {"from": 5.0, "to": 22.5}) == -1.0

    def test_midpoint_returns_half(self):
        # midpoint of 5..22.5 is 13.75
        result = _interpolated_delta(13.75, -1.0, {"from": 5.0, "to": 22.5})
        assert result == -0.5

    def test_clamped_below(self):
        assert _interpolated_delta(0, -1.0, {"from": 5.0, "to": 22.5}) == 0.0

    def test_clamped_above(self):
        assert _interpolated_delta(100, -1.0, {"from": 5.0, "to": 22.5}) == -1.0


# --------------------------------------------------------------------------
# End-to-end rule evaluation
# --------------------------------------------------------------------------


class TestEvaluate:
    def test_high_sugar_fires(self, ruleset):
        product = Product(
            name="test",
            nutrition=NutritionFacts(sugar_g=30.0),
        )
        hits = evaluate(product, ruleset)
        rule_ids = {h.rule_id for h in hits}
        assert "sugar_high" in rule_ids
        assert "sugar_moderate" not in rule_ids  # mutually exclusive bands

    def test_moderate_sugar_fires_with_interpolation(self, ruleset):
        product = Product(
            name="test",
            nutrition=NutritionFacts(sugar_g=13.75),  # exact midpoint
        )
        hits = evaluate(product, ruleset)
        sugar_hit = next(h for h in hits if h.rule_id == "sugar_moderate")
        # midpoint should give half the -1.0 penalty
        assert sugar_hit.delta == -0.5

    def test_low_sugar_does_not_penalize(self, ruleset):
        product = Product(
            name="test",
            nutrition=NutritionFacts(sugar_g=2.0),
        )
        hits = evaluate(product, ruleset)
        rule_ids = {h.rule_id for h in hits}
        assert "sugar_high" not in rule_ids
        assert "sugar_moderate" not in rule_ids

    def test_missing_nutrient_skipped_silently(self, ruleset):
        product = Product(name="test", nutrition=NutritionFacts())  # all None
        hits = evaluate(product, ruleset)
        # No nutrient rules should fire when all values are None
        nutrient_hits = [h for h in hits if h.observed_value is not None and h.rule_id.startswith(("sugar", "sat_fat", "sodium", "protein", "fiber"))]
        assert nutrient_hits == []

    def test_additive_count_with_cap(self, ruleset):
        product = Product(
            name="test",
            flagged_additive_classes=["color", "preservative", "emulsifier", "stabilizer"],  # 4 additives
        )
        hits = evaluate(product, ruleset)
        additive_hit = next(h for h in hits if h.rule_id == "additives_flagged")
        # 4 * -1.0 = -4.0, capped at -2.0
        assert additive_hit.delta == -2.0

    def test_nova_4_fires_ultra_processed(self, ruleset):
        product = Product(name="test", nova_class=4)
        hits = evaluate(product, ruleset)
        rule_ids = {h.rule_id for h in hits}
        assert "ultra_processed" in rule_ids

    def test_nova_1_does_not_fire_ultra_processed(self, ruleset):
        product = Product(name="test", nova_class=1)
        hits = evaluate(product, ruleset)
        rule_ids = {h.rule_id for h in hits}
        assert "ultra_processed" not in rule_ids

    def test_protein_high_gives_bonus(self, ruleset):
        product = Product(
            name="test",
            nutrition=NutritionFacts(protein_g=15.0),
        )
        hits = evaluate(product, ruleset)
        protein_hit = next(h for h in hits if h.rule_id == "protein_high")
        assert protein_hit.delta == 1.0

    def test_every_hit_has_a_source(self, ruleset, cereal):
        hits = evaluate(cereal, ruleset)
        assert len(hits) > 0
        for hit in hits:
            assert hit.source.org  # non-empty
            assert hit.source.type
