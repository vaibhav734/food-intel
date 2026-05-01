# Rules Reference

Human-readable catalog of every rule the engine evaluates. The authoritative source is `backend/src/food_intel/core/rules/config/rules_v1.yaml`; this document explains intent and shows what each rule does.

When rules are tuned or added, this file should be updated alongside the YAML.

## Current version: 1.0.0

The version string is recorded on every `ScoringResult` so historical scores remain reproducible after rule changes.

## Score formula

```
raw_score   = 10 + Σ(rule_deltas)
final_score = clamp(round(raw_score), 0, 10)
```

Score starts at 10 and rules add or subtract deltas. See `docs/scoring-model.md` for the full rationale.

## Verdict bands

| Score | Verdict |
|-------|---------|
| 9–10 | Excellent |
| 7–8 | Good |
| 4–6 | Moderate |
| 0–3 | Limit |

## Nutrient rules (per 100g)

### Sugar

| Rule | Trigger | Delta | Source |
|------|---------|-------|--------|
| `sugar_high` | sugar > 22.5g | −2.5 | WHO — Sugars intake guideline 2015 |
| `sugar_moderate` | 5g ≤ sugar < 22.5g | −1.0 (interpolated) | UK FSA — Front-of-pack labelling |

The moderate rule scales linearly: at 5g the penalty is 0, at 22.5g it's the full −1.0. This avoids cliffs where 22.4g and 22.6g produce wildly different scores.

### Saturated fat

| Rule | Trigger | Delta | Source |
|------|---------|-------|--------|
| `sat_fat_high` | sat fat > 5.0g | −2.0 | UK FSA |
| `sat_fat_moderate` | 1.5g ≤ sat fat < 5.0g | −0.75 (interpolated) | UK FSA |

### Sodium

| Rule | Trigger | Delta | Source |
|------|---------|-------|--------|
| `sodium_high` | sodium > 600mg | −2.0 | WHO — Sodium intake guideline 2012 |
| `sodium_moderate` | 120mg ≤ sodium < 600mg | −0.75 (interpolated) | UK FSA |

WHO recommends < 2g sodium/day. 600mg per 100g is the threshold above which a single serving can contribute disproportionately.

### Protein

| Rule | Trigger | Delta | Source |
|------|---------|-------|--------|
| `protein_low` | protein < 3.0g | −0.5 | USDA |
| `protein_high` | protein ≥ 8.0g | +1.0 | USDA |

A bonus rule, not a penalty avoidance — high-protein foods get an explicit positive nudge.

### Fiber

| Rule | Trigger | Delta | Source |
|------|---------|-------|--------|
| `fiber_high` | fiber ≥ 6.0g | +1.5 | FDA — "Excellent source" threshold |

The largest single bonus in the system. Fiber is the strongest signal for whole-food vs ultra-processed status.

## Composition rules

### Additives

| Rule | Trigger | Delta | Source |
|------|---------|-------|--------|
| `additives_flagged` | ≥ 1 flagged class | −1.0 per class, capped at −2.0 | EFSA — EU additives database |

The cap matters: a product with 5 flagged additives doesn't score lower than one with 2. We're flagging *whether* a product is heavily additive-based, not punishing per-additive ad infinitum.

Flagged classes (from `additives_v1.yaml`):
- color (E100–199)
- preservative (E200–299)
- antioxidant (E300–321)
- emulsifier (E322–399)
- stabilizer (E400–499)
- acidity_regulator (E500–599)
- flavor_enhancer (E600–699)
- glazing_agent (E900–949)
- sweetener (E950–969)

Plus 30+ named additives without E-numbers (MSG, BHT, aspartame, carrageenan, etc.).

### Ultra-processed (NOVA-4)

| Rule | Trigger | Delta | Source |
|------|---------|-------|--------|
| `ultra_processed` | nova_class == 4 | −1.5 | NOVA — Monteiro et al. classification |

NOVA-4 is the most heavily processed category — instant noodles, sugary cereals, packaged baked goods. The penalty is significant because NOVA-4 status correlates with multiple problematic markers that aren't otherwise captured (cosmetic additives, novel ingredients, formulation complexity).

If `nova_class` is not provided, this rule does not fire — it's not inferred. NOVA classification is a separate analytical step that should be supplied externally.

## Worked examples

### Plain rolled oats (clean whole food)

```
sugar=1g, sat_fat=1.2g, sodium=5mg, protein=13g, fiber=10g, NOVA=1
```

Rules fired:
- `protein_high`: +1.0
- `fiber_high`: +1.5

Raw: 10 + 1.0 + 1.5 = 12.5 → clamped to 10. **Excellent.**

### Sugar-frosted cereal

```
sugar=25g, sat_fat=2g, sodium=450mg, protein=7g, fiber=4g, NOVA=4
+ 2 flagged additive classes (color, preservative)
```

Rules fired:
- `sugar_high`: −2.5
- `sat_fat_moderate` (interpolated at 2.0/5.0): ≈ −0.11
- `sodium_moderate` (interpolated): ≈ −0.52
- `additives_flagged` (2 classes): −2.0
- `ultra_processed`: −1.5

Raw: 10 − 2.5 − 0.11 − 0.52 − 2.0 − 1.5 = 3.37 → 3. **Limit.**

### Instant noodles

```
sugar=3g, sat_fat=7g, sodium=1400mg, protein=4g, fiber=1g, NOVA=4
+ 3 flagged additive classes
```

Rules fired:
- `sat_fat_high`: −2.0
- `sodium_high`: −2.0
- `additives_flagged` (3 classes capped at −2.0): −2.0
- `ultra_processed`: −1.5

Raw: 10 − 2.0 − 2.0 − 2.0 − 1.5 = 2.5 → 2. **Limit.**

## Adding a new rule

1. Append to `rules_v1.yaml` with a unique `id`, threshold or condition, and source citation.
2. Bump the `version` field at the top of the YAML.
3. Add a unit test in `tests/unit/test_rules_engine.py` covering when the rule does and does not fire.
4. Update the golden example tests if existing products' scores would change.
5. Update this document with the new rule's row.

The rules YAML is the single source of truth. Don't add Python conditional logic to bypass it — if a case isn't expressible as a rule, the rule schema needs to be extended.
