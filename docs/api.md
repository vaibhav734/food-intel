# API Reference

The HTTP contract for the Food Intelligence Platform backend. The auto-generated Swagger UI at `/docs` is always the most current version of this — this document explains intent and gives examples.

Base URL: `http://localhost:8000` in dev. Configure for production deployments.

## Endpoints

### `GET /health`

Liveness check.

**Response 200:**
```json
{ "status": "ok" }
```

### `GET /ready`

Readiness check. Currently identical to `/health` because the core has no external dependencies that need to be reachable. When persistence is added, this endpoint will verify connection.

**Response 200:**
```json
{ "status": "ready" }
```

### `POST /analyze`

Score a food product against the rules engine.

**Request body:**

```json
{
  "name": "Sugar-Frosted Corn Cereal",
  "barcode": "0123456789012",
  "nutrition": {
    "calories_kcal": 380,
    "sugar_g": 25.0,
    "saturated_fat_g": 2.0,
    "sodium_mg": 450,
    "protein_g": 7.0,
    "fiber_g": 4.0,
    "serving_size_g": 30
  },
  "ingredients_raw": "corn, sugar, glucose syrup, salt, color (E150d), BHT",
  "nova_class": 4
}
```

Required: `name`. Everything else is optional. Missing nutrition values lower confidence but never block scoring.

All nutrition values are **per 100g**. Per-serving values must be normalized client-side before submission. This is a deliberate constraint to keep rule thresholds uniform.

**Response 200:**

```json
{
  "product_name": "Sugar-Frosted Corn Cereal",
  "barcode": "0123456789012",
  "scoring": {
    "score": 3,
    "raw_score": 3.377,
    "verdict": "Limit",
    "confidence": "high",
    "completeness": 1.0,
    "missing_fields": [],
    "reasons": [
      {
        "rule_id": "sugar_high",
        "text": "High sugar relative to guideline",
        "delta": -2.5,
        "source": {
          "org": "WHO",
          "type": "guideline",
          "doc": "Guideline: Sugars intake for adults and children, 2015"
        },
        "observed_value": 25.0,
        "threshold": 22.5
      }
    ],
    "rules_version": "1.0.0"
  },
  "explanation": "Sugar-Frosted Corn Cereal scored 3 out of 10 (Limit). Key factors: high sugar relative to guideline (per WHO), contains flagged additive classes (per EFSA), and ultra-processed food (NOVA category 4) (per NOVA)."
}
```

The response separates deterministic facts (`scoring`) from the LLM-generated `explanation` so clients can render them differently — the score and reasons are facts, the explanation is prose grounded in those facts.

**Response 422 — validation error:**

Returned when the request body fails Pydantic validation (negative nutrient values, NOVA class outside 1–4, missing `name`, oversized strings, etc.). FastAPI provides detailed field-by-field errors.

### `GET /product/{barcode}`

Look up a product by barcode (via OpenFoodFacts) and analyze it. The barcode must be all digits, 4–32 characters.

**Response 200:** identical shape to `POST /analyze`.

**Response 404:** No product found for the supplied barcode.

**Response 422:** Barcode failed format validation (non-digits, wrong length).

**Response 503:** Product lookup is disabled (`FOOD_INTEL_ENABLE_OPENFOODFACTS=false`).

OpenFoodFacts coverage is best in Europe and varies elsewhere. The lookup is best-effort — if upstream times out or returns malformed data, the endpoint returns 404 rather than crashing.

## Field reference

### Request

| Field | Type | Constraints |
|-------|------|-------------|
| `name` | string | Required, 1–200 chars |
| `barcode` | string? | Max 32 chars |
| `nutrition.calories_kcal` | number? | ≥ 0 |
| `nutrition.sugar_g` | number? | ≥ 0 |
| `nutrition.saturated_fat_g` | number? | ≥ 0 |
| `nutrition.sodium_mg` | number? | ≥ 0 |
| `nutrition.protein_g` | number? | ≥ 0 |
| `nutrition.fiber_g` | number? | ≥ 0 |
| `nutrition.serving_size_g` | number? | > 0 |
| `ingredients_raw` | string? | Max 5000 chars |
| `nova_class` | integer? | 1–4 |

### Response — `scoring` object

| Field | Type | Notes |
|-------|------|-------|
| `score` | integer | 0–10, clamped and rounded |
| `raw_score` | number | Pre-clamp, pre-round; for debugging |
| `verdict` | string | `Excellent`, `Good`, `Moderate`, `Limit` |
| `confidence` | string | `high`, `medium`, `low` |
| `completeness` | number | 0.0–1.0, weighted data completeness |
| `missing_fields` | string[] | Fields that contributed to lowered confidence |
| `reasons` | Reason[] | Every fired rule, in declaration order |
| `rules_version` | string | Version of the YAML rule file used |

### `Reason` shape

| Field | Type | Notes |
|-------|------|-------|
| `rule_id` | string | Stable identifier from the rules YAML |
| `text` | string | Human-readable summary |
| `delta` | number | Signed contribution to the score |
| `source.org` | string | `WHO`, `FDA`, `USDA`, `EFSA`, `NOVA`, `UK FSA` |
| `source.type` | string | `guideline`, `label-derived`, or `computed` |
| `source.doc` | string? | Optional citation reference |
| `observed_value` | number? | The actual value that triggered the rule |
| `threshold` | number? | The threshold the value was compared against |

Every reason has a non-empty `source.org`. This is enforced by the test suite — it's the explainability contract.

## Constraints to be aware of

- **No medical claims.** Explanations are constrained at the prompt level to avoid words like "healthy", "unsafe", "should avoid", "diagnose", "cure". The deterministic null fallback is similarly worded.
- **Source citations are required.** Every rule fires with a non-empty `source`. The test suite verifies this for all golden examples.
- **Scores are reproducible.** Same input + same `rules_version` always produces the same numeric score. The explanation text may vary slightly when an LLM is involved (low temperature, but not zero); the deterministic null provider produces stable text.
- **No PII storage.** The API is stateless. Requests are not persisted.

## Future endpoints

Not yet built:

- `POST /analyze/batch` — score multiple products in one call
- `GET /rules` — return the active rule set, for transparency
- `GET /openapi.json` — already provided by FastAPI

When new endpoints land, they'll appear in `/docs` first; this file is a narrative reference, the OpenAPI schema is authoritative.
