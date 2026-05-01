"""
SQLite product lookup adapter.

Queries a local SQLite database populated by scripts/import_off_dump.py.
Falls back gracefully if the DB file doesn't exist.
"""

from __future__ import annotations

import logging
import sqlite3
from pathlib import Path
from typing import Optional

from food_intel.core.models import NutritionFacts, Product

log = logging.getLogger(__name__)

DEFAULT_DB_PATH = Path(__file__).parents[5] / "backend" / "data" / "products.db"


class SqliteProductLookup:
    def __init__(self, db_path: Optional[Path] = None):
        self._db_path = db_path or DEFAULT_DB_PATH
        self._available = self._db_path.exists()
        if not self._available:
            log.info("SQLite product DB not found at %s — lookup disabled", self._db_path)

    def get_by_barcode(self, barcode: str) -> Optional[Product]:
        if not self._available:
            return None
        try:
            with sqlite3.connect(self._db_path) as conn:
                conn.row_factory = sqlite3.Row
                row = conn.execute(
                    "SELECT * FROM products WHERE barcode = ?", (barcode,)
                ).fetchone()
        except Exception as exc:
            log.warning("SQLite lookup error for %s: %s", barcode, exc)
            return None

        if row is None:
            return None

        return Product(
            name=row["name"] or "Unknown",
            barcode=barcode,
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
