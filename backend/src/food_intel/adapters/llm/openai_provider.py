"""
OpenAI provider for explanation generation.

Mirrors AnthropicExplanationProvider exactly — same prompt, same fallback
behavior on errors, same constraint that the LLM only rephrases the
deterministic ScoringResult, never re-scores.

The OpenAI SDK import is lazy so the package is usable without `openai`
installed (you'd just use NullExplanationProvider or AnthropicProvider
instead).
"""

from __future__ import annotations

import logging

from food_intel.adapters.llm.null_provider import NullExplanationProvider
from food_intel.core.models import Product, ScoringResult

log = logging.getLogger(__name__)


SYSTEM_PROMPT = """You are an explanation writer for a food analysis system.

Your only job is to rephrase a deterministic scoring result into clear,
neutral prose for end users. You must follow these rules:

1. Use ONLY the facts provided. Do not invent rules, reasons, or sources.
2. Do not re-score, dispute the score, or compute anything yourself.
3. Use neutral language. Avoid: "healthy", "unhealthy", "safe", "unsafe",
   "good for you", "bad for you", "prevents", "causes", "treats".
4. Acceptable framing: "compared to guideline", "based on label data",
   "according to <SOURCE>".
5. Never recommend dietary changes or medical action.
6. Reference at least one source organization (e.g. WHO, FDA, USDA, NOVA)
   from the rule hits you summarize.
7. Keep it to 2–4 sentences, plain text, no markdown.

If the confidence level is low, mention this in your final sentence."""


class OpenAIExplanationProvider:
    """Implements ExplanationProvider using OpenAI's chat completions API."""

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o-mini",
        max_tokens: int = 300,
    ):
        self.api_key = api_key
        self.model = model
        self.max_tokens = max_tokens
        self._fallback = NullExplanationProvider()
        self._client = None  # lazy-init

    def _get_client(self):
        """Lazy import + init so the SDK is optional."""
        if self._client is None:
            try:
                from openai import OpenAI
            except ImportError:
                log.warning("openai SDK not installed; using null fallback")
                return None
            self._client = OpenAI(api_key=self.api_key)
        return self._client

    def generate_explanation(
        self,
        product: Product,
        result: ScoringResult,
    ) -> str:
        client = self._get_client()
        if client is None:
            return self._fallback.generate_explanation(product, result)

        user_message = self._build_user_message(product, result)

        try:
            response = client.chat.completions.create(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=0.2,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_message},
                ],
            )
            text = (response.choices[0].message.content or "").strip()
            if not text:
                log.warning("OpenAI returned empty content; falling back")
                return self._fallback.generate_explanation(product, result)
            return text
        except Exception as exc:  # noqa: BLE001 — fall back on any error
            log.warning("OpenAI call failed (%s); falling back", exc)
            return self._fallback.generate_explanation(product, result)

    @staticmethod
    def _build_user_message(product: Product, result: ScoringResult) -> str:
        """Render the deterministic facts into a prompt-friendly form."""
        lines = [
            f"Product: {product.name}",
            f"Score: {result.score}/10 ({result.verdict.value})",
            f"Confidence: {result.confidence.value}",
        ]
        if result.missing_fields:
            lines.append(f"Missing data fields: {', '.join(result.missing_fields)}")

        lines.append("")
        lines.append("Rule hits (these are the ONLY reasons you may cite):")
        if not result.reasons:
            lines.append("  (none — score reflects baseline)")
        for hit in result.reasons:
            obs = f" [observed: {hit.observed_value}]" if hit.observed_value is not None else ""
            lines.append(
                f"  - {hit.text} (delta {hit.delta:+.2f}, "
                f"source: {hit.source.org}){obs}"
            )

        lines.append("")
        lines.append(
            "Write a 2–4 sentence neutral explanation suitable for an end user. "
            "Reference at least one source organization from the rule hits."
        )
        return "\n".join(lines)
