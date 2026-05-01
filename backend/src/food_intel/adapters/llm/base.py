"""
LLM adapter pattern.

The deterministic core never imports any LLM SDK directly. Instead, the
service layer depends on the `ExplanationProvider` protocol. Concrete
providers (Anthropic, OpenAI, null) implement it.

This is the single seam that keeps the core pure and the LLM swappable.
The LLM is constrained to ONE job: turning a structured ScoringResult
into a friendly human-readable explanation. It does not score, does not
calculate, does not pick rules.

Adding a new provider:
  1. Implement ExplanationProvider in a new module
  2. Register it in api/deps.py via the factory
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from food_intel.core.models import Product, ScoringResult


@runtime_checkable
class ExplanationProvider(Protocol):
    """
    Single-method contract for explanation generation.

    Implementations MUST:
      - Use only the data in `product` and `result` — no external calls
        for additional facts about the product
      - Return plain text suitable for direct display to end users
      - Stay neutral: no "healthy" / "unhealthy" / "safe" / "unsafe" /
        medical advice / disease prevention claims
      - Reference rule hits and their sources, not invent reasons

    Implementations SHOULD:
      - Be deterministic when possible (low temperature)
      - Fail gracefully — return a safe fallback if the LLM call errors
    """

    def generate_explanation(
        self,
        product: Product,
        result: ScoringResult,
    ) -> str:
        ...
