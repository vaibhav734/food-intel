"""
Null explanation provider.

Builds an explanation from the rule hits using a deterministic template.
No LLM calls, no network, no external dependencies. This is:

  - The default when no LLM is configured
  - The provider used in unit tests (no mocking needed)
  - The fallback when an LLM provider raises an exception
  - Useful in privacy-sensitive deployments where no data should leave

The output is plain prose — not pretty, but accurate and traceable. Every
sentence corresponds to a rule hit or a confidence note.
"""

from __future__ import annotations

from food_intel.core.models import Product, ScoringResult


class NullExplanationProvider:
    """Template-based explanation. Implements ExplanationProvider."""

    def generate_explanation(
        self,
        product: Product,
        result: ScoringResult,
    ) -> str:
        sentences: list[str] = []

        # Opening: score + verdict
        sentences.append(
            f"{product.name} scored {result.score} out of 10 ({result.verdict.value})."
        )

        # Body: top reasons (sorted by absolute impact, biggest first)
        if result.reasons:
            sorted_hits = sorted(result.reasons, key=lambda h: -abs(h.delta))
            top = sorted_hits[:3]
            phrases = []
            for hit in top:
                phrases.append(f"{hit.text.lower()} (per {hit.source.org})")
            if len(phrases) == 1:
                sentences.append(f"The main factor was {phrases[0]}.")
            else:
                joined = ", ".join(phrases[:-1]) + f", and {phrases[-1]}"
                sentences.append(f"Key factors: {joined}.")

        # Confidence caveat if relevant
        if result.confidence.value == "low":
            missing = ", ".join(result.missing_fields[:3]) if result.missing_fields else "key data"
            sentences.append(
                f"Confidence in this score is low because {missing} "
                f"could not be determined from the available data."
            )
        elif result.confidence.value == "medium":
            sentences.append(
                "Confidence is moderate — some nutrition fields were missing."
            )

        return " ".join(sentences)
