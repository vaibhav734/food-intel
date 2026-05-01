"""
Scoring engine.

Combines a list of RuleHits into a final 0..10 integer score and a verdict.

The model:
    raw_score   = 10 + sum(hit.delta for hit in hits)
    final_score = clamp(round(raw_score), 0, 10)

The verdict is derived from the final score using bands defined in the
rules YAML. This keeps the score-to-label mapping configurable alongside
the rule weights themselves.
"""

from __future__ import annotations

from typing import Any

from food_intel.core.models import RuleHit, Verdict


BASE_SCORE: float = 10.0
MIN_SCORE: int = 0
MAX_SCORE: int = 10


def compute_raw_score(hits: list[RuleHit]) -> float:
    """Sum of base + all rule deltas. May be outside [0, 10]."""
    return BASE_SCORE + sum(hit.delta for hit in hits)


def compute_final_score(raw: float) -> int:
    """Round and clamp to the 0..10 integer display range."""
    return max(MIN_SCORE, min(MAX_SCORE, round(raw)))


def derive_verdict(score: int, bands: list[dict[str, Any]]) -> Verdict:
    """
    Pick the verdict for a given score using the configured bands.

    Bands are evaluated in declaration order, and the first whose `min`
    is met wins. The YAML lists them highest-first, so this works correctly
    without sorting.
    """
    for band in bands:
        if score >= band["min"]:
            return Verdict(band["verdict"])
    # Defensive fallback — config should always include a min: 0 band
    return Verdict.LIMIT


def score(hits: list[RuleHit], verdict_bands: list[dict[str, Any]]) -> tuple[int, float, Verdict]:
    """
    The full scoring pipeline.

    Returns (final_score, raw_score, verdict). Both scores are returned so
    callers can persist the raw value for debugging while displaying the
    rounded one to users.
    """
    raw = compute_raw_score(hits)
    final = compute_final_score(raw)
    verdict = derive_verdict(final, verdict_bands)
    return final, raw, verdict
