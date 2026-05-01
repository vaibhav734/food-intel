# Scoring Model

This document defines the math the engine uses. It's the source of truth for the formula, the thresholds, and the worked examples that the golden tests verify against.

## Formula

```
raw_score   = 10 + Σ(rule_deltas)
final_score = clamp(round(raw_score), 0, 10)
```

The score starts at 10 (the default assumption is "this product is fine") and rule hits add or subtract from it. Each fired rule contributes one signed delta. Bonuses are positive, penalties are negative. The total is rounded and clamped to the displayed 0–10 range.

### Why start at 10 and subtract?

It makes the explainability guarantee airtight. You can always answer "why isn't this a 10?" by listing the penalties. There's no opaque "base score adjustment" or compositional weighting that's hard to trace.

### Why bounded penalties?

Each rule contributes at most a fixed maximum so no single nutrient dominates pathologically. A product with extreme sugar and nothing else doesn't score lower than a product with multiple moderate issues across categories. Composition is what produces low scores.

### Why round at the end?

Users see an integer 0–10. Internal math stays in floats so traces remain accurate, but the final display is clean. The raw score is preserved on every result for debugging.

## Rule thresholds (v1.0.0)

All thresholds are per-100g. Per-serving inputs need normalization upstream before reaching the rules engine.

| Nutrient | Low (bonus) | Moderate | High (penalty) | Source |
|----------|-------------|----------|----------------|--------|
| Sugar | ≤ 5 g | 5–22.5 g | > 22.5 g | UK FSA / WHO free sugars |
| Saturated fat | ≤ 1.5 g | 1.5–5 g | > 5 g | UK FSA |
| Sodium | ≤ 120 mg | 120–600 mg | > 600 mg | UK FSA / WHO |
| Protein | < 3 g (mild penalty) | 3–8 g | ≥ 8 g (bonus) | USDA |
| Fiber | < 3 g (no effect) | 3–6 g | ≥ 6 g (bonus) | FDA |

### Rule weights

| Rule | Delta |
|------|-------|
| `sugar_high` | −2.5 |
| `sugar_moderate` | −1.0 (interpolated) |
| `sat_fat_high` | −2.0 |
| `sat_fat_moderate` | −0.75 (interpolated) |
| `sodium_high` | −2.0 |
| `sodium_moderate` | −0.75 (interpolated) |
| `protein_low` | −0.5 |
| `protein_high` | +1.0 |
| `fiber_high` | +1.5 |
| `additives_flagged` | −1.0 per class, capped at −2.0 |
| `ultra_processed` | −1.5 (NOVA-4 trigger) |

### Why these weights?

They're calibrated so that:

- A clean whole food (oats, plain yogurt) lands at 9–10.
- A typical packaged snack lands at 4–7.
- An aggressively processed item (sugary cereal, instant noodles) lands at 1–3.
- No single rule pushes a score below 4 alone — only stacking does.

Sugar is the most heavily weighted because it has the strongest evidence base. Saturated fat and sodium are slightly lower because their published guidelines have more variance. Bonuses (protein, fiber) are smaller in magnitude than penalties because food processing tends to add deficits faster than it adds nutritional positives.

### Linear interpolation

Inside the moderate bands, penalties scale linearly between the thresholds rather than stepping. This avoids the cliff problem where 22.4g sugar scores very differently from 22.6g.

For sugar between 5g and 22.5g:
- At exactly 5g: −0.0
- At exactly 13.75g (midpoint): −0.5
- At exactly 22.5g: −1.0

Interpolation is configured per rule via the `interpolate: { from, to }` block in YAML. Rules without it apply their full delta whenever the condition fires.

## Verdict bands

The 0–10 score maps to a verdict label using the bands in the YAML config:

| Score | Verdict |
|-------|---------|
| 9–10 | Excellent |
| 7–8 | Good |
| 4–6 | Moderate |
| 0–3 | Limit |

These cutoffs are a product decision, not a math decision. They should be recalibrated once a real catalog has been scored — the score *distribution* should match the verdict distribution you want users to see.

## Confidence

Confidence reflects how much we trust the score given the input data. It does NOT suppress the score — low-confidence results are still returned, just flagged.

```
required_fields = {
  sugar_g:         0.25
  saturated_fat_g: 0.20
  sodium_mg:       0.20
  protein_g:       0.15
  serving_size_g:  0.10
  ingredients_raw: 0.10
}

completeness = Σ(weight_i for each field present)

confidence = "high"   if completeness ≥ 0.85
           = "medium" if completeness ≥ 0.55
           = "low"    otherwise
```

Field weights reflect importance to the score, not how often they're missing. Sugar gets the highest weight because more rules depend on it. Serving size gets lower weight because the current rules don't use it (it's there for future per-serving display logic).

## Worked examples

These are the three products in the golden test suite. The scores below are what the live engine produces — if these change after a rule edit, the golden tests fail and force you to update either the design doc or the rule edit.

### Example A: Plain rolled oats (per 100g)

```
sugar:         1.0 g    →  no penalty
sat fat:       1.2 g    →  no penalty
sodium:        5 mg     →  no penalty
protein:      13.0 g    →  +1.0 (protein_high)
fiber:        10.0 g    →  +1.5 (fiber_high)
NOVA class:   1
additives:    none

raw_score   = 10 + 1.0 + 1.5 = 12.5
final_score = clamp(round(12.5), 0, 10) = 10
verdict     = Excellent
```

### Example B: Sugar-frosted corn cereal (per 100g)

```
sugar:        25.0 g    →  −2.5 (sugar_high)
sat fat:       2.0 g    →  −0.107 (sat_fat_moderate, interpolated)
sodium:        450 mg   →  −0.516 (sodium_moderate, interpolated)
protein:       7.0 g    →  no effect (3–8 g band)
fiber:         4.0 g    →  no effect (3–6 g band)
additives:    [color, antioxidant]   →  −2.0 (2 × −1.0, no cap)
NOVA class:   4         →  −1.5 (ultra_processed)

raw_score   = 10 − 2.5 − 0.107 − 0.516 − 2.0 − 1.5 = 3.377
final_score = clamp(round(3.377), 0, 10) = 3
verdict     = Limit
```

### Example C: Instant noodles (per 100g, prepared)

```
sugar:         3.0 g    →  no penalty
sat fat:       7.0 g    →  −2.0 (sat_fat_high)
sodium:       1400 mg   →  −2.0 (sodium_high)
protein:       4.0 g    →  no effect
fiber:         1.0 g    →  no effect
additives:    [flavor enhancer, color, stabilizer]   →  3 × −1.0 = −3.0, capped at −2.0
NOVA class:   4         →  −1.5

raw_score   = 10 − 2.0 − 2.0 − 2.0 − 1.5 = 2.5
final_score = clamp(round(2.5), 0, 10) = 2
verdict     = Limit
```

Note: Python's `round()` uses banker's rounding (round-half-to-even), so 2.5 rounds to 2, not 3. This is documented in the test suite to prevent surprise.

## Updating the model

When changing rules:

1. Edit `backend/src/food_intel/core/rules/config/rules_v1.yaml`.
2. Bump the version at the top of the file (e.g. `1.0.0` → `1.1.0`).
3. Run the test suite. The golden examples will likely fail — this is expected.
4. Update this document's worked examples with the new numbers.
5. Update the test ranges in `test_golden_examples.py` if the new numbers fall outside them.
6. Commit everything together so historical scores remain reproducible: a rules version + the corresponding rule file + the corresponding test expectations.

For larger changes (new rule types, new condition operators), update `core/rules/engine.py` and add unit tests for the new primitive in `test_rules_engine.py`.
