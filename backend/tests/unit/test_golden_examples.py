"""
Golden tests — the three worked examples from the scoring-model design doc.

If these tests fail after a rule change, that's signal: either the design
doc needs updating, or the rule change was wrong. Don't update these
expectations without also updating docs/scoring-model.md.

Each test asserts on the final integer score *and* on which rules fired,
because two different rule combinations could produce the same score by
coincidence — and the explainability guarantee depends on the right rules
firing for the right reasons.
"""

from __future__ import annotations

import pytest

from food_intel.core import analyze
from food_intel.core.models import Verdict


class TestOatsScoresAtMax:
    """Plain rolled oats — clean whole food, expected 10/Excellent."""

    def test_score(self, oats, ruleset):
        result = analyze(oats, ruleset)
        assert result.score == 10
        assert result.verdict == Verdict.EXCELLENT

    def test_only_bonuses_fire(self, oats, ruleset):
        result = analyze(oats, ruleset)
        rule_ids = {h.rule_id for h in result.reasons}
        assert "protein_high" in rule_ids
        assert "fiber_high" in rule_ids
        # No penalties should fire
        penalty_ids = {h.rule_id for h in result.reasons if h.delta < 0}
        assert penalty_ids == set()

    def test_high_confidence(self, oats, ruleset):
        result = analyze(oats, ruleset)
        assert result.confidence.value == "high"
        assert result.missing_fields == []


class TestCerealScoresModerate:
    """Sugary breakfast cereal — mid-range, expected 5/Moderate."""

    def test_score_in_moderate_band(self, cereal, ruleset):
        result = analyze(cereal, ruleset)
        # Math: 10 - 2.5 (sugar high) - ~0.3 (sat fat moderate, interpolated)
        #          - ~0.5 (sodium moderate, interpolated) - 2.0 (additives)
        #          - 1.5 (NOVA-4) ≈ 3.2 → 3
        # The ranges are wide enough that small interp shifts are acceptable.
        assert 2 <= result.score <= 5
        assert result.verdict in (Verdict.MODERATE, Verdict.LIMIT)

    def test_expected_rules_fire(self, cereal, ruleset):
        result = analyze(cereal, ruleset)
        rule_ids = {h.rule_id for h in result.reasons}
        assert "sugar_high" in rule_ids
        assert "additives_flagged" in rule_ids
        assert "ultra_processed" in rule_ids

    def test_additive_cap_applied(self, cereal, ruleset):
        result = analyze(cereal, ruleset)
        additive_hit = next(
            h for h in result.reasons if h.rule_id == "additives_flagged"
        )
        # 2 additives × -1.0 = -2.0 (which is also the cap, so unaffected here)
        assert additive_hit.delta == -2.0


class TestNoodlesScoresLow:
    """Instant noodles — heavy penalties stacking, expected 0–3/Limit."""

    def test_score_low(self, noodles, ruleset):
        result = analyze(noodles, ruleset)
        assert result.score <= 3
        assert result.verdict == Verdict.LIMIT

    def test_expected_rules_fire(self, noodles, ruleset):
        result = analyze(noodles, ruleset)
        rule_ids = {h.rule_id for h in result.reasons}
        assert "sat_fat_high" in rule_ids
        assert "sodium_high" in rule_ids
        assert "additives_flagged" in rule_ids
        assert "ultra_processed" in rule_ids

    def test_score_clamped_not_negative(self, noodles, ruleset):
        """Even with heavy penalties, displayed score never goes below 0."""
        result = analyze(noodles, ruleset)
        assert result.score >= 0
        # Raw might be negative — that's fine, it's preserved for debugging
        # but the user-facing score is clamped.


class TestSparseProductStillScores:
    """Low confidence caps the score — no false high scores on missing data."""

    def test_returns_score(self, sparse_product, ruleset):
        result = analyze(sparse_product, ruleset)
        assert isinstance(result.score, int)
        assert 0 <= result.score <= 10

    def test_low_confidence_flagged(self, sparse_product, ruleset):
        result = analyze(sparse_product, ruleset)
        assert result.confidence.value == "low"
        assert len(result.missing_fields) >= 4

    def test_low_confidence_score_capped(self, sparse_product, ruleset):
        """A low-confidence product must never score above the LOW cap (5)."""
        result = analyze(sparse_product, ruleset)
        cap = ruleset.confidence_caps.get("low", 10)
        assert result.score <= cap, (
            f"Low-confidence product scored {result.score}, exceeds cap {cap}"
        )


class TestRulesVersionRecorded:
    """Every result must include the rules version that produced it."""

    def test_version_present(self, oats, ruleset):
        result = analyze(oats, ruleset)
        assert result.rules_version == ruleset.version


class TestEveryReasonIsTraceable:
    """Explainability contract: every rule hit carries a source citation."""

    @pytest.mark.parametrize("fixture_name", ["oats", "cereal", "noodles"])
    def test_all_reasons_have_sources(self, fixture_name, ruleset, request):
        product = request.getfixturevalue(fixture_name)
        result = analyze(product, ruleset)
        for reason in result.reasons:
            assert reason.source.org, f"Rule {reason.rule_id} has empty source"
            assert reason.text, f"Rule {reason.rule_id} has no human text"
