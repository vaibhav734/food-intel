"""
Demo: run the three worked examples and pretty-print results.

This is the kind of thing you'd extract into a real CLI later, but for now
it's a sanity-check you can run after any rule change to see the impact.

    PYTHONPATH=src python scripts/demo.py
"""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from food_intel.core import NutritionFacts, Product, analyze, load_ruleset


RULES_PATH = Path(__file__).parent.parent / "src" / "food_intel" / "core" / "rules" / "config" / "rules_v1.yaml"


PRODUCTS = [
    Product(
        name="Plain Rolled Oats",
        nutrition=NutritionFacts(
            calories_kcal=379, sugar_g=1.0, saturated_fat_g=1.2,
            sodium_mg=5, protein_g=13.0, fiber_g=10.0, serving_size_g=40,
        ),
        ingredients_raw="100% rolled oats",
        nova_class=1,
    ),
    Product(
        name="Sugar-Frosted Corn Cereal",
        nutrition=NutritionFacts(
            calories_kcal=380, sugar_g=25.0, saturated_fat_g=2.0,
            sodium_mg=450, protein_g=7.0, fiber_g=4.0, serving_size_g=30,
        ),
        ingredients_raw="corn, sugar, glucose syrup, salt, color (E160a), BHT",
        flagged_additive_classes=["color", "antioxidant"],
        nova_class=4,
    ),
    Product(
        name="Instant Noodles, Spicy",
        nutrition=NutritionFacts(
            calories_kcal=450, sugar_g=3.0, saturated_fat_g=7.0,
            sodium_mg=1400, protein_g=4.0, fiber_g=1.0, serving_size_g=85,
        ),
        ingredients_raw="wheat flour, palm oil, salt, MSG, color (E150d)",
        flagged_additive_classes=["flavor enhancer", "color", "stabilizer"],
        nova_class=4,
    ),
]


def main() -> None:
    ruleset = load_ruleset(RULES_PATH)
    print(f"Loaded ruleset v{ruleset.version} with {len(ruleset.rules)} rules\n")
    print("=" * 72)

    for product in PRODUCTS:
        result = analyze(product, ruleset)
        print(f"\n{product.name}")
        print("-" * len(product.name))
        print(f"  Score:      {result.score}/10  ({result.verdict.value})")
        print(f"  Raw:        {result.raw_score}")
        print(f"  Confidence: {result.confidence.value} ({result.completeness:.0%} complete)")
        print(f"  Reasons ({len(result.reasons)}):")
        for hit in result.reasons:
            sign = "+" if hit.delta >= 0 else ""
            obs = f" [observed: {hit.observed_value}]" if hit.observed_value is not None else ""
            print(f"    {sign}{hit.delta:>5}  {hit.text}{obs}")
            print(f"           source: {hit.source.org} ({hit.source.type.value})")

    print("\n" + "=" * 72)


if __name__ == "__main__":
    main()
