"""
Seed data lookup — fills gaps for known products missing from upstream APIs.

Loaded from seed_data.yaml at startup. Checked before any network call,
so it works fully offline and takes priority over incomplete upstream data.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import yaml

from food_intel.core.models import NutritionFacts, Product

_SEED_PATH = Path(__file__).parent / "seed_data.yaml"


def _load() -> dict[str, dict]:
    if not _SEED_PATH.exists():
        return {}
    with _SEED_PATH.open() as f:
        raw = yaml.safe_load(f) or {}
    return {str(k): v for k, v in (raw.get("products") or {}).items()}


_SEED: dict[str, dict] = _load()


def get_by_barcode(barcode: str) -> Optional[Product]:
    entry = _SEED.get(barcode)
    if entry is None:
        return None

    n = entry.get("nutrition") or {}
    nova = entry.get("nova_class")

    return Product(
        name=entry.get("name", "Unknown"),
        barcode=barcode,
        nutrition=NutritionFacts(
            calories_kcal=n.get("calories_kcal"),
            sugar_g=n.get("sugar_g"),
            saturated_fat_g=n.get("saturated_fat_g"),
            sodium_mg=n.get("sodium_mg"),
            protein_g=n.get("protein_g"),
            fiber_g=n.get("fiber_g"),
            serving_size_g=n.get("serving_size_g"),
        ),
        ingredients_raw=entry.get("ingredients_raw"),
        nova_class=int(nova) if nova is not None else None,
    )
