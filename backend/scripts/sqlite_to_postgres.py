#!/usr/bin/env python3
"""
Copy the local SQLite product catalog into Postgres.

Typical use with Supabase session pooler:

    export FOOD_INTEL_PRODUCT_DB_URL='postgresql://...'
    python scripts/sqlite_to_postgres.py
"""

from __future__ import annotations

import argparse
import os
import sqlite3
from pathlib import Path

SQLITE_DEFAULT = Path(__file__).parents[1] / "data" / "products.db"

CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS products (
    barcode TEXT PRIMARY KEY,
    name TEXT,
    brand TEXT,
    quantity TEXT,
    image_front_url TEXT,
    allergens_tags TEXT,
    calories_kcal DOUBLE PRECISION,
    sugar_g DOUBLE PRECISION,
    saturated_fat_g DOUBLE PRECISION,
    sodium_mg DOUBLE PRECISION,
    protein_g DOUBLE PRECISION,
    fiber_g DOUBLE PRECISION,
    serving_size_g DOUBLE PRECISION,
    ingredients_raw TEXT,
    nova_class INTEGER,
    product_type TEXT NOT NULL DEFAULT 'food'
);
CREATE INDEX IF NOT EXISTS idx_products_barcode ON products (barcode);
"""

UPSERT_SQL = """
INSERT INTO products (
    barcode, name, brand, quantity, image_front_url, allergens_tags,
    calories_kcal, sugar_g, saturated_fat_g, sodium_mg,
    protein_g, fiber_g, serving_size_g, ingredients_raw,
    nova_class, product_type
) VALUES (
    %(barcode)s, %(name)s, %(brand)s, %(quantity)s, %(image_front_url)s, %(allergens_tags)s,
    %(calories_kcal)s, %(sugar_g)s, %(saturated_fat_g)s, %(sodium_mg)s,
    %(protein_g)s, %(fiber_g)s, %(serving_size_g)s, %(ingredients_raw)s,
    %(nova_class)s, %(product_type)s
)
ON CONFLICT (barcode) DO UPDATE SET
    name = EXCLUDED.name,
    brand = EXCLUDED.brand,
    quantity = EXCLUDED.quantity,
    image_front_url = EXCLUDED.image_front_url,
    allergens_tags = EXCLUDED.allergens_tags,
    calories_kcal = EXCLUDED.calories_kcal,
    sugar_g = EXCLUDED.sugar_g,
    saturated_fat_g = EXCLUDED.saturated_fat_g,
    sodium_mg = EXCLUDED.sodium_mg,
    protein_g = EXCLUDED.protein_g,
    fiber_g = EXCLUDED.fiber_g,
    serving_size_g = EXCLUDED.serving_size_g,
    ingredients_raw = EXCLUDED.ingredients_raw,
    nova_class = EXCLUDED.nova_class,
    product_type = EXCLUDED.product_type
"""

EXPECTED_COLUMNS = [
    "barcode",
    "name",
    "brand",
    "quantity",
    "image_front_url",
    "allergens_tags",
    "calories_kcal",
    "sugar_g",
    "saturated_fat_g",
    "sodium_mg",
    "protein_g",
    "fiber_g",
    "serving_size_g",
    "ingredients_raw",
    "nova_class",
    "product_type",
]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sqlite", type=Path, default=SQLITE_DEFAULT)
    parser.add_argument("--pg-url", default=os.environ.get("FOOD_INTEL_PRODUCT_DB_URL", ""))
    args = parser.parse_args()

    if not args.pg_url:
        raise SystemExit("Set --pg-url or FOOD_INTEL_PRODUCT_DB_URL")

    try:
        import psycopg
    except ImportError as exc:
        raise SystemExit("psycopg required: pip install psycopg[binary]") from exc

    with sqlite3.connect(args.sqlite) as sqlite_conn:
        sqlite_conn.row_factory = sqlite3.Row
        rows = sqlite_conn.execute("SELECT * FROM products").fetchall()
        payload = []
        for row in rows:
            item = {column: row[column] if column in row.keys() else None for column in EXPECTED_COLUMNS}
            if item["product_type"] is None:
                item["product_type"] = "food"
            payload.append(item)

    with psycopg.connect(args.pg_url) as pg_conn:
        with pg_conn.cursor() as cur:
            cur.execute(CREATE_TABLE)
            cur.executemany(UPSERT_SQL, payload)
        pg_conn.commit()

    print(f"Uploaded {len(payload)} products from {args.sqlite}")
