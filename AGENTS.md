# Food Intelligence Platform — AI Agent Context

## What this is
Evidence-based food scoring platform. Deterministic Python core + FastAPI backend + Vue 3 frontend.
Analyzes packaged food (nutrition values, ingredients, optional barcode) and returns a scored result with traceable rules.

## Architecture
```
backend/src/food_intel/
├── core/        # Pure domain — rules, scoring, confidence, parser (no I/O, no LLM)
├── adapters/    # LLM and product-lookup adapters
├── services/    # Orchestration — wires core + adapters
└── api/         # FastAPI routes + schemas + DI wiring

frontend/src/
├── components/  # ScoreDisplay, ReasonList, ConfidenceBadge
├── views/       # ScanView, ResultView
├── stores/      # Pinia state machine
└── api/         # Typed fetch client
```

## Hard rules
- Scoring logic is deterministic — same input + same rules = same output, always
- LLM is only used for explanation text, never for scoring decisions
- All rule thresholds live in YAML — never hardcode them in Python
- Input is always per-100g — no per-serving normalization in the engine
- New code must follow the core/adapters/services/api layering — no cross-layer shortcuts
- Do not add database persistence, auth, or async job queues without explicit discussion
- **No false claims**: a product with LOW confidence must never score above 5/10; MEDIUM above 8/10. Missing data is not evidence of quality. Confidence caps are defined in rules_v1.yaml under `confidence_caps` and enforced in `core/analyze.py`.
- Every score component must be traceable to a rule, a source citation, and observed data — no black-box outputs

## Testing
```bash
cd backend && PYTHONPATH=src python -m pytest   # 106 tests, runs fully offline
cd frontend && npm run build                    # type-check + build
```
All tests must pass before any change is considered done.

## Key docs
- `docs/architecture.md` — design rationale
- `docs/scoring-model.md` — scoring math
- `docs/rules-reference.md` — rule definitions and sources
- `docs/api.md` — API contract
