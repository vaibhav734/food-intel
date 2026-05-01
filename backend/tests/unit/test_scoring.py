"""Unit tests for the scoring engine."""

from __future__ import annotations

from food_intel.core.models import RuleHit, Source, SourceType, Verdict
from food_intel.core.scoring import (
    BASE_SCORE,
    compute_final_score,
    compute_raw_score,
    derive_verdict,
    score,
)


# A tiny helper to build RuleHits without verbose ceremony.
def _hit(delta: float) -> RuleHit:
    return RuleHit(
        rule_id="test",
        text="test",
        delta=delta,
        source=Source(org="TEST", type=SourceType.GUIDELINE),
    )


# --------------------------------------------------------------------------
# Raw score
# --------------------------------------------------------------------------


class TestRawScore:
    def test_no_hits_gives_base(self):
        assert compute_raw_score([]) == BASE_SCORE

    def test_single_penalty(self):
        assert compute_raw_score([_hit(-2.5)]) == 7.5

    def test_penalties_and_bonuses_sum(self):
        hits = [_hit(-2.5), _hit(-2.0), _hit(1.0), _hit(1.5)]
        # 10 - 2.5 - 2.0 + 1.0 + 1.5 = 8.0
        assert compute_raw_score(hits) == 8.0

    def test_can_exceed_max_before_clamp(self):
        # Bonuses alone could push raw above 10 — clamp handles this later
        assert compute_raw_score([_hit(1.0), _hit(1.5), _hit(0.5)]) == 13.0

    def test_can_go_negative_before_clamp(self):
        assert compute_raw_score([_hit(-5.0), _hit(-7.0)]) == -2.0


# --------------------------------------------------------------------------
# Final score (rounding + clamping)
# --------------------------------------------------------------------------


class TestFinalScore:
    def test_clamp_below_zero(self):
        assert compute_final_score(-3.5) == 0

    def test_clamp_above_ten(self):
        assert compute_final_score(12.5) == 10

    def test_round_to_nearest(self):
        assert compute_final_score(4.7) == 5
        assert compute_final_score(4.4) == 4

    def test_banker_rounding_half(self):
        # Python's round() uses banker's rounding; document the behavior
        # so it doesn't surprise anyone reading scores
        assert compute_final_score(2.5) == 2  # rounds to even
        assert compute_final_score(3.5) == 4


# --------------------------------------------------------------------------
# Verdict bands
# --------------------------------------------------------------------------


class TestVerdict:
    @staticmethod
    def _bands():
        # Mirrors rules_v1.yaml — kept inline to avoid coupling tests to file
        return [
            {"min": 9, "verdict": "Excellent"},
            {"min": 7, "verdict": "Good"},
            {"min": 4, "verdict": "Moderate"},
            {"min": 0, "verdict": "Limit"},
        ]

    def test_score_10_is_excellent(self):
        assert derive_verdict(10, self._bands()) == Verdict.EXCELLENT

    def test_score_9_boundary_is_excellent(self):
        assert derive_verdict(9, self._bands()) == Verdict.EXCELLENT

    def test_score_8_is_good(self):
        assert derive_verdict(8, self._bands()) == Verdict.GOOD

    def test_score_5_is_moderate(self):
        assert derive_verdict(5, self._bands()) == Verdict.MODERATE

    def test_score_3_is_limit(self):
        assert derive_verdict(3, self._bands()) == Verdict.LIMIT

    def test_score_0_is_limit(self):
        assert derive_verdict(0, self._bands()) == Verdict.LIMIT


# --------------------------------------------------------------------------
# Full pipeline
# --------------------------------------------------------------------------


class TestScorePipeline:
    def test_returns_all_three_outputs(self):
        bands = TestVerdict._bands()
        final, raw, verdict = score([_hit(-2.5)], bands)
        assert final == 8  # 10 - 2.5 = 7.5 → rounds to 8
        assert raw == 7.5
        assert verdict == Verdict.GOOD
