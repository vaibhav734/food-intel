#!/usr/bin/env python3
"""
Enrich missing nutrition data for products in the SQLite DB using Gemini AI.

Gemini is prompted to find nutrition per 100g for each product by name+barcode.
Results are written back to the DB. Skips products that already have data.

Free tier: 1500 requests/day (gemini-2.0-flash).

Usage:
    export NVIDIA_API_KEY=your_key_here
    python scripts/enrich_nutrition.py                  # local SQLite
    python scripts/enrich_nutrition.py --limit 100      # first 100
    python scripts/enrich_nutrition.py --dry-run        # preview only
    FOOD_INTEL_PRODUCT_DB_URL=postgresql://... \
      python scripts/enrich_nutrition.py                # hosted Postgres

Get a free key at: https://aistudio.google.com/apikey
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sqlite3
import time
from pathlib import Path
from typing import Optional

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

DB_PATH = Path(__file__).parents[1] / "data" / "products.db"
NVIDIA_URL = "https://integrate.api.nvidia.com/v1/chat/completions"
NVIDIA_MODEL = "meta/llama-3.3-70b-instruct"

PROMPT_TEMPLATE = """You are a nutrition database assistant. Find the nutrition facts per 100g for this Indian packaged food product.

Product name: {name}
Barcode: {barcode}

Search for this product and return ONLY a JSON object with these fields (use null if unknown):
{{
  "calories_kcal": <number or null>,
  "sugar_g": <number or null>,
  "saturated_fat_g": <number or null>,
  "sodium_mg": <number or null>,
  "protein_g": <number or null>,
  "fiber_g": <number or null>,
  "serving_size_g": <number or null>,
  "ingredients_raw": <string or null>,
  "nova_class": <1-4 or null>
}}

Return ONLY the JSON, no explanation."""


def query_nvidia(api_key: str, name: str, barcode: str) -> Optional[dict]:
    try:
        import httpx
    except ImportError:
        raise RuntimeError("httpx required: pip install httpx")

    payload = {
        "model": NVIDIA_MODEL,
        "messages": [{"role": "user", "content": PROMPT_TEMPLATE.format(name=name, barcode=barcode)}],
        "temperature": 0,
        "max_tokens": 300,
    }
    headers = {"Authorization": f"Bearer {api_key}"}

    for attempt in range(4):
        try:
            r = httpx.post(NVIDIA_URL, json=payload, headers=headers, timeout=30)
            if r.status_code == 429:
                wait = 2 ** attempt * 5  # 5, 10, 20, 40s
                log.warning("Rate limited, waiting %ds (attempt %d)", wait, attempt + 1)
                time.sleep(wait)
                continue
            if r.status_code != 200:
                log.warning("NVIDIA error %s for %s: %s", r.status_code, barcode, r.text[:200])
                return None

            text = r.json()["choices"][0]["message"]["content"].strip()
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            return json.loads(text)
        except Exception as exc:
            log.warning("NVIDIA error for %s: %s", barcode, exc)
            return None

    log.warning("Gave up on %s after retries", barcode)
    return None


def _select_sqlite_rows(db_path: Path, limit: int) -> list[dict]:
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT barcode, name FROM products
            WHERE calories_kcal IS NULL AND sugar_g IS NULL
              AND protein_g IS NULL AND sodium_mg IS NULL
            ORDER BY barcode
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [dict(row) for row in rows]


def _sqlite_counts(db_path: Path) -> tuple[int, int]:
    with sqlite3.connect(db_path) as conn:
        total = conn.execute("SELECT COUNT(*) FROM products").fetchone()[0]
        missing = conn.execute(
            "SELECT COUNT(*) FROM products WHERE calories_kcal IS NULL AND sugar_g IS NULL AND protein_g IS NULL AND sodium_mg IS NULL"
        ).fetchone()[0]
    return total, missing


def _update_sqlite(db_path: Path, barcode: str, updates: dict) -> None:
    with sqlite3.connect(db_path) as conn:
        set_clause = ", ".join(f"{k} = ?" for k in updates)
        conn.execute(
            f"UPDATE products SET {set_clause} WHERE barcode = ?",
            [*updates.values(), barcode],
        )
        conn.commit()


def _select_postgres_rows(pg_url: str, limit: int) -> list[dict]:
    import psycopg
    from psycopg.rows import dict_row

    with psycopg.connect(pg_url, row_factory=dict_row) as conn:
        rows = conn.execute(
            """
            SELECT barcode, name FROM products
            WHERE calories_kcal IS NULL AND sugar_g IS NULL
              AND protein_g IS NULL AND sodium_mg IS NULL
            ORDER BY barcode
            LIMIT %s
            """,
            (limit,),
        ).fetchall()
    return list(rows)


def _postgres_counts(pg_url: str) -> tuple[int, int]:
    import psycopg

    with psycopg.connect(pg_url) as conn:
        total = conn.execute("SELECT COUNT(*) FROM products").fetchone()[0]
        missing = conn.execute(
            "SELECT COUNT(*) FROM products WHERE calories_kcal IS NULL AND sugar_g IS NULL AND protein_g IS NULL AND sodium_mg IS NULL"
        ).fetchone()[0]
    return total, missing


def _update_postgres(pg_url: str, barcode: str, updates: dict) -> None:
    import psycopg

    set_clause = ", ".join(f"{k} = %s" for k in updates)
    with psycopg.connect(pg_url) as conn:
        conn.execute(
            f"UPDATE products SET {set_clause} WHERE barcode = %s",
            [*updates.values(), barcode],
        )
        conn.commit()


def enrich(
    *,
    db_path: Optional[Path],
    pg_url: str,
    api_key: str,
    limit: int,
    dry_run: bool,
) -> None:
    if pg_url:
        rows = _select_postgres_rows(pg_url, limit)
    else:
        assert db_path is not None
        rows = _select_sqlite_rows(db_path, limit)

    total = len(rows)
    log.info("Products to enrich: %d", total)

    updated = skipped = failed = 0

    for i, row in enumerate(rows, 1):
        barcode, name = row["barcode"], row["name"]
        log.info("[%d/%d] %s — %s", i, total, barcode, name)

        if dry_run:
            log.info("  DRY RUN — skipping API call")
            continue

        data = query_nvidia(api_key, name, barcode)
        if data is None:
            failed += 1
        else:
            fields = [
                "calories_kcal",
                "sugar_g",
                "saturated_fat_g",
                "sodium_mg",
                "protein_g",
                "fiber_g",
                "serving_size_g",
                "ingredients_raw",
                "nova_class",
            ]
            updates = {f: data[f] for f in fields if f in data and data[f] is not None}

            if not updates:
                log.info("  No data found")
                skipped += 1
            else:
                if pg_url:
                    _update_postgres(pg_url, barcode, updates)
                else:
                    assert db_path is not None
                    _update_sqlite(db_path, barcode, updates)
                log.info("  Updated: %s", {k: v for k, v in updates.items() if k != "ingredients_raw"})
                updated += 1

        time.sleep(0.5)

    log.info("Done. Updated: %d | No data: %d | Failed: %d / %d total",
             updated, skipped, failed, total)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=500, help="Max products to process (default 500)")
    parser.add_argument("--db", type=Path, default=DB_PATH)
    parser.add_argument("--pg-url", default=os.environ.get("FOOD_INTEL_PRODUCT_DB_URL", ""))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    api_key = os.environ.get("NVIDIA_API_KEY", "")
    if not api_key and not args.dry_run:
        print("Set NVIDIA_API_KEY env var. Get a free key at https://build.nvidia.com/")
        return

    if args.pg_url:
        total, missing = _postgres_counts(args.pg_url)
    else:
        total, missing = _sqlite_counts(args.db)
    log.info("DB stats — Total: %d | Missing all nutrition: %d", total, missing)

    enrich(
        db_path=None if args.pg_url else args.db,
        pg_url=args.pg_url,
        api_key=api_key,
        limit=args.limit,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main()
