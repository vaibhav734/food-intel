"""
OpenFoodFacts product lookup adapter.

OpenFoodFacts is a free, open-data food product database with a JSON API.
See https://world.openfoodfacts.org/api

This adapter:
  - Takes a barcode, returns a Product or None
  - Maps OpenFoodFacts field names to our NutritionFacts shape
  - Handles missing fields gracefully (most products have gaps)
  - Does NOT run the ingredient parser — that's the service layer's job
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from food_intel.adapters.product_lookup.base import ProductLookup
from food_intel.core.models import NutritionFacts, Product

log = logging.getLogger(__name__)

DEFAULT_BASE_URL = "https://world.openfoodfacts.org/api/v2/product"
DEFAULT_TIMEOUT = 5.0  # seconds


class OpenFoodFactsLookup:
    """Implements ProductLookup against OpenFoodFacts."""

    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = DEFAULT_TIMEOUT,
        user_agent: str = "FoodIntelligencePlatform/0.1",
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.user_agent = user_agent

    def get_by_barcode(self, barcode: str) -> Optional[Product]:
        # Lazy import — only require httpx if this adapter is actually used
        try:
            import httpx
        except ImportError as exc:
            raise RuntimeError(
                "httpx is required for OpenFoodFactsLookup; "
                "install with `pip install httpx`"
            ) from exc

        url = f"{self.base_url}/{barcode}.json"
        try:
            response = httpx.get(
                url,
                timeout=self.timeout,
                headers={"User-Agent": self.user_agent},
            )
        except httpx.HTTPError as exc:
            log.warning("OpenFoodFacts request failed for %s: %s", barcode, exc)
            return None

        if response.status_code == 404:
            return None
        if response.status_code != 200:
            log.warning(
                "OpenFoodFacts returned %s for %s",
                response.status_code, barcode,
            )
            return None

        data = response.json()
        if data.get("status") != 1 or "product" not in data:
            return None

        return self._map_product(data["product"], barcode)

    @staticmethod
    def _map_product(raw: dict[str, Any], barcode: str) -> Product:
        """Map OpenFoodFacts product dict → our Product model."""
        nutriments = raw.get("nutriments", {}) or {}

        nutrition = NutritionFacts(
            calories_kcal=_get_float(nutriments, "energy-kcal_100g"),
            sugar_g=_get_float(nutriments, "sugars_100g"),
            saturated_fat_g=_get_float(nutriments, "saturated-fat_100g"),
            sodium_mg=_get_sodium_mg(nutriments),
            protein_g=_get_float(nutriments, "proteins_100g"),
            fiber_g=_get_float(nutriments, "fiber_100g"),
            serving_size_g=_get_serving_size_g(raw),
        )

        nova_class = raw.get("nova_group")
        if nova_class is not None:
            try:
                nova_class = int(nova_class)
            except (ValueError, TypeError):
                nova_class = None

        return Product(
            name=raw.get("product_name") or raw.get("generic_name") or "Unknown",
            barcode=barcode,
            nutrition=nutrition,
            ingredients_raw=raw.get("ingredients_text") or None,
            nova_class=nova_class,
        )


# ---------------------------------------------------------------------------
# Field mapping helpers
# ---------------------------------------------------------------------------

def _get_float(d: dict[str, Any], key: str) -> Optional[float]:
    """Coerce to float, returning None for missing/invalid values."""
    value = d.get(key)
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def _get_sodium_mg(nutriments: dict[str, Any]) -> Optional[float]:
    """
    OpenFoodFacts can report either sodium or salt, sometimes both, in
    grams per 100g. Convert to mg.
    Salt → sodium: divide by 2.5 (NaCl is ~40% sodium by mass).
    """
    sodium_g = _get_float(nutriments, "sodium_100g")
    if sodium_g is not None:
        return round(sodium_g * 1000, 2)

    salt_g = _get_float(nutriments, "salt_100g")
    if salt_g is not None:
        return round((salt_g / 2.5) * 1000, 2)

    return None


def _get_serving_size_g(raw: dict[str, Any]) -> Optional[float]:
    """
    serving_size is a free-text field on OFF (e.g. "30g", "1 cup (240ml)").
    We extract a leading numeric value followed by 'g' if present.
    """
    text = raw.get("serving_size")
    if not text:
        return None
    import re
    match = re.match(r"\s*([\d.]+)\s*g\b", text)
    if not match:
        return None
    try:
        return float(match.group(1))
    except ValueError:
        return None
