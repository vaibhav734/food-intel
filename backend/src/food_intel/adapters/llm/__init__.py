"""LLM adapter package — explanation providers."""

from food_intel.adapters.llm.anthropic_provider import AnthropicExplanationProvider
from food_intel.adapters.llm.base import ExplanationProvider
from food_intel.adapters.llm.null_provider import NullExplanationProvider
from food_intel.adapters.llm.openai_provider import OpenAIExplanationProvider

__all__ = [
    "AnthropicExplanationProvider",
    "ExplanationProvider",
    "NullExplanationProvider",
    "OpenAIExplanationProvider",
]
