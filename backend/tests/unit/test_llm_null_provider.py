"""Tests for the null explanation provider."""

from __future__ import annotations

from food_intel.adapters.llm import NullExplanationProvider
from food_intel.core.models import (
    Confidence,
    NutritionFacts,
    Product,
    RuleHit,
    ScoringResult,
    Source,
    SourceType,
    Verdict,
)


def _make_result(
    score: int = 5,
    verdict: Verdict = Verdict.MODERATE,
    confidence: Confidence = Confidence.HIGH,
    reasons=None,
    missing=None,
) -> ScoringResult:
    return ScoringResult(
        score=score,
        raw_score=float(score),
        verdict=verdict,
        reasons=reasons or [],
        confidence=confidence,
        completeness=1.0 if confidence == Confidence.HIGH else 0.4,
        missing_fields=missing or [],
        rules_version="1.0.0",
    )


def _hit(text: str, delta: float, org: str = "WHO") -> RuleHit:
    return RuleHit(
        rule_id="test", text=text, delta=delta,
        source=Source(org=org, type=SourceType.GUIDELINE),
    )


class TestNullProvider:
    def test_includes_score_and_verdict(self):
        provider = NullExplanationProvider()
        product = Product(name="Test Product")
        result = _make_result(score=7, verdict=Verdict.GOOD)
        text = provider.generate_explanation(product, result)
        assert "Test Product" in text
        assert "7" in text
        assert "Good" in text

    def test_lists_top_reasons(self):
        provider = NullExplanationProvider()
        product = Product(name="Snack")
        result = _make_result(
            reasons=[
                _hit("High sugar", -2.5, "WHO"),
                _hit("High sodium", -2.0, "WHO"),
            ],
        )
        text = provider.generate_explanation(product, result)
        assert "high sugar" in text.lower()
        assert "WHO" in text

    def test_low_confidence_caveat(self):
        provider = NullExplanationProvider()
        product = Product(name="Mystery")
        result = _make_result(
            confidence=Confidence.LOW,
            missing=["sugar_g", "saturated_fat_g"],
        )
        text = provider.generate_explanation(product, result)
        assert "low" in text.lower() or "could not" in text.lower()

    def test_no_reasons_still_produces_output(self):
        provider = NullExplanationProvider()
        product = Product(name="Plain Water")
        result = _make_result(score=10, verdict=Verdict.EXCELLENT, reasons=[])
        text = provider.generate_explanation(product, result)
        assert text  # non-empty
        assert "10" in text

    def test_deterministic(self):
        provider = NullExplanationProvider()
        product = Product(name="X")
        result = _make_result(reasons=[_hit("Test", -1.0)])
        a = provider.generate_explanation(product, result)
        b = provider.generate_explanation(product, result)
        assert a == b
