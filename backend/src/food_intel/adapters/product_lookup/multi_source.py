"""
Multi-source product lookup adapter.

Tries data sources in priority order and merges results to fill gaps.
Sources used (all free, open, no API key required by default):

  1. OpenFoodFacts  — food products worldwide (https://world.openfoodfacts.org)
  2. Open Beauty Facts — cosmetics (https://world.openbeautyfacts.org)
  3. USDA FoodData Central — authoritative US nutrition data (https://fdc.nal.usda.gov)
     Requires a free API key: https://fdc.nal.usda.gov/api-key-signup.html

The merger fills None fields from later sources, so a product found in
OpenFoodFacts with missing sodium can be enriched by USDA data.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from food_intel.adapters.product_lookup.base import ProductLookup
from food_intel.adapters.product_lookup import seed_lookup
from food_intel.adapters.product_lookup.sqlite_lookup import SqliteProductLookup
from food_intel.core.models import NutritionFacts, Product

log = logging.getLogger(__name__)

_OFF_BASE = "https://world.openfoodfacts.org/api/v2/product"
_OBF_BASE = "https://world.openbeautyfacts.org/api/v2/product"
_USDA_BASE = "https://api.nal.usda.gov/fdc/v1"
_TIMEOUT = 6.0
_UA = "FoodIntelligencePlatform/1.0 (open-source; contact via GitHub)"


class MultiSourceLookup:
    """
    Implements ProductLookup by querying multiple open databases and
    merging the results to maximise data completeness.
    """

    def __init__(self, usda_api_key: Optional[str] = None, db_path: Optional[Path] = None):
        self._usda_key = usda_api_key
        self._sqlite = SqliteProductLookup(db_path) if db_path else SqliteProductLookup()

    def get_by_barcode(self, barcode: str) -> Optional[Product]:
        # 1. Seed data — offline, authoritative for known products
        product = seed_lookup.get_by_barcode(barcode)
        if product is not None:
            return product

        # 2. Local SQLite DB (populated from OFF dump)
        product = self._sqlite.get_by_barcode(barcode)
        if product is not None:
            return product

        try:
            import httpx
        except ImportError as exc:
            raise RuntimeError("httpx required; pip install httpx") from exc

        with httpx.Client(timeout=_TIMEOUT, headers={"User-Agent": _UA}) as client:
            product = _try_off(client, barcode, _OFF_BASE)
            if product is None:
                product = _try_off(client, barcode, _OBF_BASE)
            if product is not None and self._usda_key:
                product = _enrich_from_usda(client, product, self._usda_key)

        return product


# ---------------------------------------------------------------------------
# OpenFoodFacts / OpenBeautyFacts (same API shape)
# ---------------------------------------------------------------------------

def _try_off(client: Any, barcode: str, base_url: str) -> Optional[Product]:
    url = f"{base_url}/{barcode}.json"
    try:
        r = client.get(url)
    except Exception as exc:
        log.warning("Lookup failed %s: %s", url, exc)
        return None

    if r.status_code != 200:
        return None
    data = r.json()
    if data.get("status") != 1 or "product" not in data:
        return None

    return _map_off_product(data["product"], barcode)


def _map_off_product(raw: dict[str, Any], barcode: str) -> Product:
    n = raw.get("nutriments") or {}

    # Detect product type from OFF categories
    categories = (raw.get("categories_tags") or [])
    product_type = "food"
    if any("baby" in c or "infant" in c for c in categories):
        product_type = "baby_food"
    elif base_url_is_beauty := any(
        k in raw for k in ("periods_after_opening", "ph_value")
    ):
        product_type = "cosmetic"

    nova = raw.get("nova_group")
    try:
        nova = int(nova) if nova is not None else None
    except (ValueError, TypeError):
        nova = None

    return Product(
        name=raw.get("product_name") or raw.get("generic_name") or "Unknown",
        barcode=barcode,
        nutrition=NutritionFacts(
            calories_kcal=_f(n, "energy-kcal_100g"),
            sugar_g=_f(n, "sugars_100g"),
            saturated_fat_g=_f(n, "saturated-fat_100g"),
            sodium_mg=_sodium_mg(n),
            protein_g=_f(n, "proteins_100g"),
            fiber_g=_f(n, "fiber_100g"),
            serving_size_g=_serving_g(raw),
        ),
        ingredients_raw=raw.get("ingredients_text") or None,
        nova_class=nova,
        product_type=product_type,
    )


# ---------------------------------------------------------------------------
# USDA FoodData Central enrichment (fills gaps in nutrition data)
# ---------------------------------------------------------------------------

def _enrich_from_usda(client: Any, product: Product, api_key: str) -> Product:
    """Search USDA by product name and merge any missing nutrition fields."""
    if not product.name or product.name == "Unknown":
        return product

    try:
        r = client.get(
            f"{_USDA_BASE}/foods/search",
            params={"query": product.name, "pageSize": 1, "api_key": api_key},
        )
        if r.status_code != 200:
            return product
        foods = r.json().get("foods") or []
        if not foods:
            return product
    except Exception as exc:
        log.warning("USDA search failed for '%s': %s", product.name, exc)
        return product

    usda_nutrients = {n["nutrientName"]: n.get("value") for n in foods[0].get("foodNutrients", [])}

    n = product.nutrition
    # Only fill fields that are currently None
    merged = NutritionFacts(
        calories_kcal=n.calories_kcal if n.calories_kcal is not None else _usda_float(usda_nutrients, "Energy"),
        sugar_g=n.sugar_g if n.sugar_g is not None else _usda_float(usda_nutrients, "Total Sugars"),
        saturated_fat_g=n.saturated_fat_g if n.saturated_fat_g is not None else _usda_float(usda_nutrients, "Fatty acids, total saturated"),
        sodium_mg=n.sodium_mg if n.sodium_mg is not None else _usda_float(usda_nutrients, "Sodium, Na"),
        protein_g=n.protein_g if n.protein_g is not None else _usda_float(usda_nutrients, "Protein"),
        fiber_g=n.fiber_g if n.fiber_g is not None else _usda_float(usda_nutrients, "Fiber, total dietary"),
        serving_size_g=n.serving_size_g,
    )
    product.nutrition = merged
    return product


def _usda_float(nutrients: dict[str, Any], name: str) -> Optional[float]:
    val = nutrients.get(name)
    try:
        return float(val) if val is not None else None
    except (ValueError, TypeError):
        return None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _f(d: dict[str, Any], key: str) -> Optional[float]:
    v = d.get(key)
    if v is None or v == "":
        return None
    try:
        return float(v)
    except (ValueError, TypeError):
        return None


def _sodium_mg(n: dict[str, Any]) -> Optional[float]:
    s = _f(n, "sodium_100g")
    if s is not None:
        return round(s * 1000, 2)
    salt = _f(n, "salt_100g")
    if salt is not None:
        return round((salt / 2.5) * 1000, 2)
    return None


def _serving_g(raw: dict[str, Any]) -> Optional[float]:
    import re
    text = raw.get("serving_size")
    if not text:
        return None
    m = re.match(r"\s*([\d.]+)\s*g\b", text)
    return float(m.group(1)) if m else None
