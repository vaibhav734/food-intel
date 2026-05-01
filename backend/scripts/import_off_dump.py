#!/usr/bin/env python3
"""
Import Open Food Facts dump into a local SQLite database.

Downloads the OFF JSONL dump (world or India-filtered), extracts relevant
fields, and inserts into data/products.db.

Usage:
    # Full world dump filtered to India (recommended, ~2-3 GB download):
    python scripts/import_off_dump.py

    # Use a pre-downloaded file:
    python scripts/import_off_dump.py --file /path/to/openfoodfacts-products.jsonl.gz

    # Dry run — show stats without writing DB:
    python scripts/import_off_dump.py --dry-run
"""

from __future__ import annotations

import argparse
import gzip
import json
import logging
import re
import sqlite3
import sys
import urllib.request
from pathlib import Path
from typing import Any, Optional

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

DUMP_URL = "https://static.openfoodfacts.org/data/openfoodfacts-products.jsonl.gz"
DATA_DIR = Path(__file__).parents[1] / "data"
DB_PATH = DATA_DIR / "products.db"

CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS products (
    barcode          TEXT PRIMARY KEY,
    name             TEXT,
    calories_kcal    REAL,
    sugar_g          REAL,
    saturated_fat_g  REAL,
    sodium_mg        REAL,
    protein_g        REAL,
    fiber_g          REAL,
    serving_size_g   REAL,
    ingredients_raw  TEXT,
    nova_class       INTEGER,
    product_type     TEXT NOT NULL DEFAULT 'food'
);
CREATE INDEX IF NOT EXISTS idx_barcode ON products(barcode);
"""


def _f(d: dict, key: str) -> Optional[float]:
    v = d.get(key)
    if v is None or v == "":
        return None
    try:
        return float(v)
    except (ValueError, TypeError):
        return None


def _sodium_mg(n: dict) -> Optional[float]:
    s = _f(n, "sodium_100g")
    if s is not None:
        mg = round(s * 1000, 2)
        return mg if mg <= 10000 else None  # >10g sodium/100g is impossible
    salt = _f(n, "salt_100g")
    if salt is not None:
        mg = round((salt / 2.5) * 1000, 2)
        return mg if mg <= 10000 else None
    return None


def _serving_g(raw: dict) -> Optional[float]:
    text = raw.get("serving_size")
    if not text:
        return None
    m = re.match(r"\s*([\d.]+)\s*g\b", str(text))
    return float(m.group(1)) if m else None


def _product_type(raw: dict) -> str:
    categories = raw.get("categories_tags") or []
    if any("baby" in c or "infant" in c for c in categories):
        return "baby_food"
    if any(k in raw for k in ("periods_after_opening", "ph_value")):
        return "cosmetic"
    return "food"


def _is_india(raw: dict) -> bool:
    countries = raw.get("countries_tags") or []
    return any("india" in c.lower() for c in countries)


def parse_product(raw: dict) -> Optional[tuple]:
    barcode = str(raw.get("code") or "").strip()
    if not barcode or not barcode.isdigit():
        return None

    name = (raw.get("product_name") or raw.get("generic_name") or "").strip()
    if not name:
        return None

    n = raw.get("nutriments") or {}
    nova = raw.get("nova_group")
    try:
        nova = int(nova) if nova is not None else None
    except (ValueError, TypeError):
        nova = None

    calories = _f(n, "energy-kcal_100g")
    sugar = _f(n, "sugars_100g")

    # Sanity clamps — bad crowd-sourced data
    if calories is not None and calories > 900:
        calories = None
    if sugar is not None and sugar > 100:
        sugar = None

    return (
        barcode,
        name,
        calories,
        sugar,
        _f(n, "saturated-fat_100g"),
        _sodium_mg(n),
        _f(n, "proteins_100g"),
        _f(n, "fiber_100g"),
        _serving_g(raw),
        (raw.get("ingredients_text") or "").strip() or None,
        nova,
        _product_type(raw),
    )


def download_dump(dest: Path) -> None:
    log.info("Downloading OFF dump from %s", DUMP_URL)
    log.info("This is ~9 GB — will take a while. Press Ctrl+C to cancel.")

    def _progress(count, block_size, total):
        if total > 0:
            pct = min(count * block_size * 100 / total, 100)
            print(f"\r  {pct:.1f}%  ({count * block_size / 1e9:.2f} GB)", end="", flush=True)

    urllib.request.urlretrieve(DUMP_URL, dest, reporthook=_progress)
    print()
    log.info("Downloaded to %s", dest)


def import_dump(src: Path, db_path: Path, dry_run: bool = False) -> None:
    DATA_DIR.mkdir(exist_ok=True)

    if not dry_run:
        conn = sqlite3.connect(db_path)
        conn.executescript(CREATE_TABLE)
        conn.commit()

    total = india = inserted = skipped = 0
    batch = []
    BATCH_SIZE = 5000

    def flush(conn, batch):
        conn.executemany(
            "INSERT OR REPLACE INTO products VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", batch
        )
        conn.commit()

    log.info("Reading %s ...", src)
    opener = gzip.open if src.suffix == ".gz" else open

    with opener(src, "rt", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            total += 1
            if total % 100_000 == 0:
                log.info("  processed %d k lines, india=%d, inserted=%d", total // 1000, india, inserted)

            try:
                raw = json.loads(line)
            except json.JSONDecodeError:
                skipped += 1
                continue

            if not _is_india(raw):
                continue
            india += 1

            row = parse_product(raw)
            if row is None:
                skipped += 1
                continue

            if dry_run:
                inserted += 1
                continue

            batch.append(row)
            if len(batch) >= BATCH_SIZE:
                flush(conn, batch)
                inserted += len(batch)
                batch.clear()

    if not dry_run and batch:
        flush(conn, batch)
        inserted += len(batch)
        conn.close()

    log.info("Done. Total lines: %d | India products: %d | Inserted: %d | Skipped: %d",
             total, india, inserted, skipped)
    if not dry_run:
        log.info("Database written to %s", db_path)


def main() -> None:
    parser = argparse.ArgumentParser(description="Import OFF dump into SQLite")
    parser.add_argument("--file", type=Path, help="Path to existing .jsonl or .jsonl.gz dump")
    parser.add_argument("--db", type=Path, default=DB_PATH, help="Output SQLite DB path")
    parser.add_argument("--dry-run", action="store_true", help="Count only, don't write DB")
    args = parser.parse_args()

    src = args.file
    if src is None:
        src = DATA_DIR / "openfoodfacts-products.jsonl.gz"
        if not src.exists():
            download_dump(src)

    if not src.exists():
        log.error("Dump file not found: %s", src)
        sys.exit(1)

    import_dump(src, args.db, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
