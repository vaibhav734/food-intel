# Architecture

This document explains how the Food Intelligence Platform is structured and why. It's the reference for understanding *why* the code is the way it is — the rules and scoring math live in `scoring-model.md`, and the HTTP contract lives in `api.md`.

## Guiding principles

Four decisions shape everything else.

### 1. The deterministic core is a pure library

The scoring engine, rule engine, ingredient parser, and confidence calculation all live in `backend/src/food_intel/core/` with zero I/O — no database, no HTTP, no LLM calls. This means:

- It's trivially testable. Unit tests are pure-function assertions, no mocks.
- It's reproducible. Given a product and a rules version, you get the same output every time, forever.
- It can be lifted anywhere. The same code works in a CLI, a notebook, a batch job, or a different web framework — without modification.

The FastAPI layer is one consumer of this library; if we ever build a CLI or a Slack bot, they call directly into `core.analyze()` too.

### 2. The LLM is an adapter behind an interface

The core never imports `anthropic` or `openai`. It depends on the `ExplanationProvider` Protocol (`adapters/llm/base.py`) with a single method: `generate_explanation(result, product_name) -> str`.

Concrete providers (`AnthropicExplanationProvider`, `NullExplanationProvider`) implement that protocol. Swapping providers, mocking them in tests, or running offline becomes trivial — and crucially, the system never crashes when the LLM does. If the Anthropic API is down or rate-limited, the provider catches the exception and falls back to the deterministic null provider.

The LLM is also constrained at the prompt level. The system prompt (`EXPLANATION_SYSTEM_PROMPT`) explicitly forbids prescriptive language ("should avoid", "healthy", "diagnose") and caps output at 80 words. The LLM does NOT score, NOT calculate, NOT pick rules — it summarizes a structured result.

### 3. Data flows one direction

Raw input → normalized product → scored result → explanation. No backwards dependencies, no service calling another service that calls the first.

```
Request (HTTP) → AnalyzeRequest schema → Product → core.analyze()
                                                       ↓
                                                 ScoringResult
                                                       ↓
                                              AnalyzeService
                                                       ↓
                                              ExplanationProvider
                                                       ↓
                                                AnalysisResult
                                                       ↓
                                            AnalyzeResponse → HTTP
```

This keeps the dependency graph acyclic and makes every component independently testable. The only place where core and adapters meet is in `services/analyze.py`, which is the deliberate orchestration seam.

### 4. Rules are data, not code

Thresholds, weights, and source citations live in `core/rules/config/rules_v1.yaml`. The same applies to the additives catalog (`additives_v1.yaml`). Rules are loaded into dataclasses at startup; the engine is configuration-driven.

This buys three things:

1. Nutritionists can review and tune rules via PR without writing Python.
2. Every score records `rules_version: "1.0.0"`. Historical scores remain reproducible after rule tuning.
3. Adding new rules doesn't require code changes — just YAML edits and tests.

The format is intentionally simple. Anything more complex (cross-nutrient logic, conditional rules) should compose existing rules rather than extending the YAML grammar.

## Layered structure

```
api/         FastAPI routes, schemas, dependency wiring     ← HTTP boundary
services/    Orchestration: ties core + adapters together   ← single seam
core/        Pure domain: rules, scoring, confidence        ← never imports
                                                              from outside
adapters/    LLM providers, future persistence/lookups       ← implements
                                                              core's needs
```

The architectural rule is: **anything in `core/` can never import from `adapters/`, `api/`, or `services/`**. The dependency arrow always points inward. This is enforceable with a tool like `import-linter` if the codebase grows large enough to need it.

## What this architecture refuses to do

A few deliberate omissions:

- **No microservices.** It's a monolith with clean internal boundaries. Splitting prematurely is how MVPs die. Boundaries are clean enough that splitting later (if load demands it) is a few days of work, not a rewrite.
- **No event bus or job queue.** `/analyze` is synchronous. If LLM latency becomes a UX problem, the right fix is streaming the response, not async job queues.
- **No user accounts in v1.** No auth, no personalization. Adds significant surface area for no current product benefit.
- **No caching layer (Redis).** Postgres can handle thousands of analyses per minute. Add caching when measurement shows a problem, not before.

Each is a "say no for now" decision, not a "never." The architecture leaves room for all of them without paying their cost upfront.

## Models and schemas: three distinct shapes

A common FastAPI mistake is using one Pydantic class as the API schema, the database model, and the domain model. They look similar at first but diverge fast — the API wants validation rules and stable field names, the database wants indexes and migration-friendly columns, the domain wants rich behavior.

This codebase uses three separate shapes:

- `core/models.py` — domain dataclasses (`Product`, `NutritionFacts`, `ScoringResult`)
- `api/schemas.py` — Pydantic request/response (validation, OpenAPI docs)
- `adapters/persistence/schema.py` — SQLAlchemy ORM (when added)

Conversion happens at the boundaries. The cost is some duplication; the benefit is each layer evolves independently.

## Configuration and dependency injection

`api/deps.py` holds the singleton wiring — ruleset, additives catalog, LLM provider, and `AnalyzeService` are all constructed once at startup using `@lru_cache`. FastAPI's `Depends()` injects them into route handlers.

Settings come from environment variables via `config.py`. The rest of the code never reads `os.environ` directly — making testing and deployment configuration changes simple.

## Testing strategy

Three test layers, each catching a different class of bug:

1. **Unit tests** (`tests/unit/`) — pure function tests. Rules engine condition primitives, scoring math, parser tokenization, confidence calculations. Fast, deterministic, no I/O.
2. **Golden examples** (`test_golden_examples.py`) — three real-ish products (oats, cereal, noodles) with expected score ranges. These are the regression net for rule changes. When you tune rule weights, golden tests tell you exactly what moved and by how much.
3. **Integration tests** (`tests/integration/`) — full HTTP round-trips against the live FastAPI app via `TestClient`. Confirms the whole stack composes correctly, including request validation and response serialization.

The LLM provider has its own tests against the null implementation; the Anthropic provider's network behavior would be tested with a mocked client (not yet wired up — easy to add when the SDK is needed in CI).
