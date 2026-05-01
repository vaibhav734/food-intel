"""
Product lookup protocol.

Same pattern as the LLM adapter — the service layer depends on this
interface, not on any specific data source. We can swap OpenFoodFacts
for an internal database, a CSV, or a mock without touching service code.
"""

from __future__ import annotations

from typing import Optional, Protocol, runtime_checkable

from food_intel.core.models import Product


class ProductNotFoundError(Exception):
    """Raised when a barcode lookup finds no matching product."""


@runtime_checkable
class ProductLookup(Protocol):
    """Look up a product by barcode."""

    def get_by_barcode(self, barcode: str) -> Optional[Product]:
        """
        Returns a fully-populated Product, or None if not found.

        Implementations should not raise on "not found" — None is the
        contract. They MAY raise on transport errors (network failures,
        rate limits) so the service layer can decide how to handle them.
        """
        ...
