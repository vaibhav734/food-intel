"""
Integration tests for the API layer.

These tests use FastAPI's TestClient — no real HTTP server, but the full
request/response/dependency-injection stack runs. They exercise:

  - Schema validation (rejecting bad input)
  - Dependency wiring (services build correctly)
  - Route handlers (correct status codes, response shapes)
  - End-to-end determinism (same request → same score)

The LLM is the null provider in tests (default settings) — no network
calls, no flakiness, no API keys needed.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from food_intel.api.app import create_app


@pytest.fixture(scope="module")
def client() -> TestClient:
    return TestClient(create_app())


# --------------------------------------------------------------------------
# Health
# --------------------------------------------------------------------------


class TestHealth:
    def test_health_returns_ok(self, client):
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json() == {"status": "ok"}

    def test_ready_returns_ready(self, client):
        r = client.get("/ready")
        assert r.status_code == 200
        assert r.json() == {"status": "ready"}


# --------------------------------------------------------------------------
# Analyze
# --------------------------------------------------------------------------


class TestAnalyze:
    def test_oats_scores_high(self, client):
        r = client.post(
            "/analyze",
            json={
                "name": "Plain Rolled Oats",
                "nutrition": {
                    "calories_kcal": 379,
                    "sugar_g": 1.0,
                    "saturated_fat_g": 1.2,
                    "sodium_mg": 5,
                    "protein_g": 13.0,
                    "fiber_g": 10.0,
                    "serving_size_g": 40,
                },
                "ingredients_raw": "100% rolled oats",
                "nova_class": 1,
            },
        )
        assert r.status_code == 200
        body = r.json()
        assert body["scoring"]["score"] == 10
        assert body["scoring"]["verdict"] == "Excellent"
        assert body["scoring"]["confidence"] == "high"
        assert body["explanation"]
        assert "Plain Rolled Oats" in body["explanation"]

    def test_noodles_scores_low(self, client):
        r = client.post(
            "/analyze",
            json={
                "name": "Instant Noodles",
                "nutrition": {
                    "sugar_g": 3, "saturated_fat_g": 7, "sodium_mg": 1400,
                    "protein_g": 4, "fiber_g": 1, "serving_size_g": 85,
                },
                "ingredients_raw": "wheat flour, palm oil, salt, MSG, color (E150d)",
                "nova_class": 4,
            },
        )
        assert r.status_code == 200
        body = r.json()
        assert body["scoring"]["score"] <= 3
        assert body["scoring"]["verdict"] == "Limit"

    def test_response_shape_has_all_required_fields(self, client):
        r = client.post(
            "/analyze",
            json={
                "name": "Test", "nutrition": {"sugar_g": 5},
            },
        )
        assert r.status_code == 200
        body = r.json()
        assert {"product_name", "scoring", "explanation"} <= body.keys()
        assert {
            "score", "raw_score", "verdict", "reasons",
            "confidence", "completeness", "missing_fields", "rules_version",
        } <= body["scoring"].keys()

    def test_every_reason_has_a_source(self, client):
        r = client.post(
            "/analyze",
            json={
                "name": "Cereal",
                "nutrition": {
                    "sugar_g": 25, "saturated_fat_g": 2, "sodium_mg": 450,
                    "protein_g": 7, "fiber_g": 4, "serving_size_g": 30,
                },
                "ingredients_raw": "corn, sugar, color (E150a)",
                "nova_class": 4,
            },
        )
        body = r.json()
        for reason in body["scoring"]["reasons"]:
            assert reason["source"]["org"]
            assert reason["source"]["type"]

    def test_deterministic_same_input_same_score(self, client):
        payload = {
            "name": "Test",
            "nutrition": {"sugar_g": 15, "saturated_fat_g": 3, "sodium_mg": 400},
        }
        r1 = client.post("/analyze", json=payload)
        r2 = client.post("/analyze", json=payload)
        assert r1.json()["scoring"]["score"] == r2.json()["scoring"]["score"]
        assert r1.json()["scoring"]["raw_score"] == r2.json()["scoring"]["raw_score"]

    def test_low_confidence_with_sparse_data(self, client):
        r = client.post("/analyze", json={"name": "Mystery", "nutrition": {"sugar_g": 10}})
        assert r.status_code == 200
        body = r.json()
        assert body["scoring"]["confidence"] == "low"
        assert len(body["scoring"]["missing_fields"]) >= 4
        # Low confidence must never produce a falsely high score
        assert body["scoring"]["score"] <= 5


# --------------------------------------------------------------------------
# Validation
# --------------------------------------------------------------------------


class TestValidation:
    def test_missing_name_rejected(self, client):
        r = client.post("/analyze", json={"nutrition": {}})
        assert r.status_code == 422

    def test_negative_sugar_rejected(self, client):
        r = client.post(
            "/analyze",
            json={"name": "Test", "nutrition": {"sugar_g": -5}},
        )
        assert r.status_code == 422

    def test_invalid_nova_class_rejected(self, client):
        r = client.post(
            "/analyze",
            json={"name": "Test", "nutrition": {}, "nova_class": 7},
        )
        assert r.status_code == 422

    def test_huge_ingredients_string_rejected(self, client):
        r = client.post(
            "/analyze",
            json={
                "name": "Test",
                "nutrition": {},
                "ingredients_raw": "x" * 6000,
            },
        )
        assert r.status_code == 422


# --------------------------------------------------------------------------
# Product lookup (validation only — we don't hit OpenFoodFacts in tests)
# --------------------------------------------------------------------------


class TestProductRoute:
    def test_invalid_barcode_format_rejected(self, client):
        # Letters not allowed by the regex
        r = client.get("/product/abc123")
        assert r.status_code == 422

    def test_too_short_barcode_rejected(self, client):
        r = client.get("/product/12")
        assert r.status_code == 422
