# Food Intelligence Platform

Evidence-based food scoring. Analyzes a packaged food product (nutrition values, ingredients, optional barcode) and returns:

1. An Eat Score (0–10) with traffic-light verdict
2. The rules that fired, each with a published-guideline source
3. A confidence assessment based on data completeness
4. A plain-text explanation grounded in those rule hits

The system never gives medical advice. It presents observed data, authoritative guideline comparisons, and computed scores — every claim is traceable to a rule and a source.

## Why it's structured this way

The deterministic core (rules, scoring, confidence, ingredient parser) is implemented in Python with zero I/O and zero LLM dependencies. The LLM is constrained to one job — turning the structured result into a friendly paragraph — and never participates in scoring. This means:

- **Scores are reproducible.** Same input + same rules version = same output, forever.
- **Tests don't need an LLM.** All 106 unit + integration tests run offline in under three seconds.
- **Rule changes are reviewable.** Thresholds, weights, and additive classifications live in YAML with semantic versioning, so historical scores stay valid after rule tuning.

See `docs/architecture.md` for the full rationale and `docs/scoring-model.md` for the math.

## Repository layout

```
food-intel/
├── backend/         # FastAPI app + deterministic scoring core
│   ├── src/food_intel/
│   │   ├── core/        # Pure domain — rules, scoring, confidence, parser
│   │   ├── adapters/    # External world — LLM and product-lookup adapters
│   │   ├── services/    # Orchestration — wires core + adapters
│   │   └── api/         # FastAPI routes + schemas + DI wiring
│   └── tests/           # unit/ + integration/
├── frontend/        # Vue 3 + Vite + Pinia (TypeScript)
│   └── src/
│       ├── components/  # ScoreDisplay, ReasonList, ConfidenceBadge, ...
│       ├── views/       # ScanView (form), ResultView (output panel)
│       ├── stores/      # Pinia: analysis state machine
│       ├── types/       # API contract types
│       └── api/         # Typed fetch client
└── docs/
    ├── architecture.md
    ├── scoring-model.md
    ├── rules-reference.md
    └── api.md
```

## Quick start

### Backend

```bash
cd backend
pip install -e ".[dev,api]"
PYTHONPATH=src python -m pytest                     # 106 tests
PYTHONPATH=src uvicorn food_intel.api.app:app --reload --port 8000
```

The API will be available at `http://localhost:8000`. Open `http://localhost:8000/docs` for the auto-generated Swagger UI.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The dev server runs at `http://localhost:5173` and proxies `/api/*` to the backend on port 8000.

### Without an LLM

The backend works fully offline. If you don't set `FOOD_INTEL_ANTHROPIC_API_KEY`, the API uses the `NullExplanationProvider` — scoring still works, explanations are template-based and deterministic.

## Configuration

Environment variables (all prefixed `FOOD_INTEL_`, all optional):

| Variable | Default | Purpose |
|----------|---------|---------|
| `LLM_PROVIDER` | `null` | `null` or `anthropic` |
| `ANTHROPIC_API_KEY` | — | Required when `LLM_PROVIDER=anthropic` |
| `ANTHROPIC_MODEL` | `claude-haiku-4-5-20251001` | Model for explanations |
| `ENABLE_OPENFOODFACTS` | `true` | Whether `/product/{barcode}` is wired up |
| `PRODUCT_DB_URL` | — | Hosted Postgres URL for barcode lookup; preferred over SQLite when set |
| `PRODUCT_DB_PATH` | auto-detect | Override local SQLite lookup DB path |
| `CORS_ORIGINS` | `http://localhost:5173` | Comma-separated allowed origins |

Settings are loaded from `.env` if present.

## Testing

106 tests across:

- **`tests/unit/`** — golden examples, rules engine, scoring math, confidence, ingredient parser, null LLM provider
- **`tests/integration/`** — full HTTP request/response round-trips against the live FastAPI app via TestClient

```bash
cd backend && PYTHONPATH=src python -m pytest
```

The frontend builds clean and type-checks with `npm run build`.

## What's deliberately not built

These are conscious omissions, not oversights — see `docs/architecture.md` for the reasoning:

- **Database persistence.** Analyses are computed on demand and not stored. Add when caching or audit trails matter.
- **Authentication.** No user accounts in v1.
- **Per-serving normalization.** The engine assumes per-100g input. US labels (per-serving) need conversion upstream.
- **Frontend tests.** Vue components rely on type-checking and the typed API client; component-level tests would be the next addition.
- **Async job queue.** Scoring is synchronous and fast enough that Celery/Redis would be premature.

## License

Internal project — no license specified.
