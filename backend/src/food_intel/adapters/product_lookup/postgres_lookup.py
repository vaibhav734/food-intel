"""
Hosted Postgres product lookup adapter.

Designed for managed Postgres instances such as Supabase. The schema mirrors
the lightweight SQLite catalog so deployments can move the lookup DB off-repo
without changing the deterministic scoring core.
"""

from __future__ import annotations

import logging
from typing import Optional

from food_intel.core.models import NutritionFacts, Product

log = logging.getLogger(__name__)


class PostgresProductLookup:
    def __init__(self, db_url: str):
        self._db_url = db_url

    def get_by_barcode(self, barcode: str) -> Optional[Product]:
        try:
            import psycopg
            from psycopg.rows import dict_row
        except ImportError as exc:
            raise RuntimeError("psycopg required; pip install psycopg[binary]") from exc

        try:
            with psycopg.connect(self._db_url, row_factory=dict_row) as conn:
                row = conn.execute(
                    """
                    SELECT barcode, name, brand, quantity, image_front_url, allergens_tags,
                           calories_kcal, sugar_g, saturated_fat_g, sodium_mg,
                           protein_g, fiber_g, serving_size_g, ingredients_raw,
                           nova_class, product_type
                    FROM products
                    WHERE barcode = %s
                    """,
                    (barcode,),
                ).fetchone()
        except Exception as exc:
            log.warning("Postgres lookup error for %s: %s", barcode, exc)
            return None

        if row is None:
            return None

        allergens_raw = row.get("allergens_tags") or ""
        allergens = [tag for tag in str(allergens_raw).split(",") if tag]

        return Product(
            name=row["name"] or "Unknown",
            barcode=barcode,
            brand=row.get("brand") or None,
            quantity=row.get("quantity") or None,
            image_front_url=row.get("image_front_url") or None,
            allergens=allergens,
            nutrition=NutritionFacts(
                calories_kcal=row["calories_kcal"],
                sugar_g=row["sugar_g"],
                saturated_fat_g=row["saturated_fat_g"],
                sodium_mg=row["sodium_mg"],
                protein_g=row["protein_g"],
                fiber_g=row["fiber_g"],
                serving_size_g=row["serving_size_g"],
            ),
            ingredients_raw=row["ingredients_raw"] or None,
            nova_class=row["nova_class"],
            product_type=row["product_type"] or "food",
        )
