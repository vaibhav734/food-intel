"""
Rules engine.

Loads rules from YAML and evaluates them against a Product, producing a list
of RuleHits. The engine is pure: same input → same output, no side effects,
no I/O after the initial load.

The engine handles three condition types:
  - Threshold-based (gt, gte, lt, lte) on numeric nutrients
  - Range-based (between) with optional linear interpolation
  - Field-based (count_gt, eq) on non-nutrient product fields

Anything more exotic should compose existing rules rather than extending
the condition vocabulary here.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import yaml

from food_intel.core.models import Product, RuleHit
from food_intel.core.rules.definitions import Rule, parse_rule


@dataclass(frozen=True)
class RuleSet:
    """A loaded, validated set of rules along with metadata."""
    version: str
    rules: list[Rule]
    verdict_bands: list[dict[str, Any]]
    confidence_caps: dict[str, int] = field(default_factory=lambda: {"low": 10, "medium": 10, "high": 10})


def load_ruleset(path: Path) -> RuleSet:
    """Load and validate a rules YAML file."""
    with path.open() as f:
        raw = yaml.safe_load(f)

    rules = [parse_rule(r) for r in raw["rules"]]
    return RuleSet(
        version=raw["version"],
        rules=rules,
        verdict_bands=raw["verdict_bands"],
        confidence_caps=raw.get("confidence_caps", {"low": 10, "medium": 10, "high": 10}),
    )


# ---------------------------------------------------------------------------
# Condition evaluators
# ---------------------------------------------------------------------------

def _check_numeric_condition(value: float, condition: dict[str, Any]) -> bool:
    """Return True if `value` satisfies the condition."""
    if "gt" in condition:
        return value > condition["gt"]
    if "gte" in condition:
        return value >= condition["gte"]
    if "lt" in condition:
        return value < condition["lt"]
    if "lte" in condition:
        return value <= condition["lte"]
    if "between" in condition:
        lo, hi = condition["between"]
        return lo <= value < hi
    if "eq" in condition:
        return value == condition["eq"]
    raise ValueError(f"Unknown numeric condition: {condition}")


def _check_count_condition(items: list, condition: dict[str, Any]) -> bool:
    """Conditions that operate on list lengths."""
    if "count_gt" in condition:
        return len(items) > condition["count_gt"]
    if "count_gte" in condition:
        return len(items) >= condition["count_gte"]
    if "count_lte" in condition:
        return len(items) <= condition["count_lte"]
    if "contains" in condition:
        return condition["contains"] in items
    raise ValueError(f"Unknown count condition: {condition}")


def _interpolated_delta(
    value: float, base_delta: float, interp: dict[str, float]
) -> float:
    """
    Scale `base_delta` linearly between interp['from'] and interp['to'].

    At `from`, returns 0 (rule has just started applying).
    At `to`, returns base_delta (rule at full strength).
    Clamped outside the range.
    """
    lo, hi = interp["from"], interp["to"]
    if value <= lo:
        return 0.0
    if value >= hi:
        return base_delta
    fraction = (value - lo) / (hi - lo)
    return base_delta * fraction


# ---------------------------------------------------------------------------
# Main evaluator
# ---------------------------------------------------------------------------

def evaluate(product: Product, ruleset: RuleSet) -> list[RuleHit]:
    """
    Apply every rule in the ruleset to the product.

    Returns a list of RuleHits in rule-definition order. Rules whose
    target field is missing on the product are silently skipped — the
    confidence engine handles missing-data accounting separately.
    """
    hits: list[RuleHit] = []

    for rule in ruleset.rules:
        hit = _evaluate_rule(product, rule)
        if hit is not None:
            hits.append(hit)

    return hits


def _evaluate_rule(product: Product, rule: Rule) -> Optional[RuleHit]:
    """Evaluate a single rule. Returns None if the rule does not fire."""
    if rule.nutrient is not None:
        return _eval_nutrient_rule(product, rule)
    if rule.field is not None:
        return _eval_field_rule(product, rule)
    return None


def _eval_nutrient_rule(product: Product, rule: Rule) -> Optional[RuleHit]:
    """Rules targeting a NutritionFacts field."""
    value = getattr(product.nutrition, rule.nutrient, None)
    if value is None:
        return None  # missing data; confidence engine will note this

    if not _check_numeric_condition(value, rule.condition):
        return None

    # Compute delta — apply interpolation if specified
    if rule.interpolate is not None:
        delta = _interpolated_delta(value, rule.delta, rule.interpolate)
    else:
        delta = rule.delta

    # Skip near-zero contributions to keep output clean
    if abs(delta) < 0.01:
        return None

    threshold = _extract_threshold(rule.condition)
    return RuleHit(
        rule_id=rule.id,
        text=rule.text,
        delta=round(delta, 3),
        source=rule.source,
        observed_value=value,
        threshold=threshold,
    )


def _eval_field_rule(product: Product, rule: Rule) -> Optional[RuleHit]:
    """Rules targeting a non-nutrition Product field."""
    value = getattr(product, rule.field, None)
    if value is None:
        return None

    # Per-unit count rules (e.g. additives_flagged)
    if rule.per_unit_penalty is not None:
        if not isinstance(value, list):
            return None
        if not _check_count_condition(value, rule.condition):
            return None
        raw_delta = rule.per_unit_penalty * len(value)
        if rule.cap is not None and raw_delta < rule.cap:
            raw_delta = rule.cap
        return RuleHit(
            rule_id=rule.id,
            text=rule.text,
            delta=round(raw_delta, 3),
            source=rule.source,
            observed_value=float(len(value)),
        )

    # List membership / count rules with fixed penalty or bonus
    if isinstance(value, list):
        if not _check_count_condition(value, rule.condition):
            return None
        return RuleHit(
            rule_id=rule.id,
            text=rule.text,
            delta=rule.delta,
            source=rule.source,
            observed_value=float(len(value)),
        )

    # Scalar field rules (e.g. nova_class == 4)
    if not isinstance(value, (int, float)):
        return None
    if not _check_numeric_condition(float(value), rule.condition):
        return None
    return RuleHit(
        rule_id=rule.id,
        text=rule.text,
        delta=rule.delta,
        source=rule.source,
        observed_value=float(value),
    )


def _extract_threshold(condition: dict[str, Any]) -> Optional[float]:
    """Pull the most relevant threshold number out of a condition dict."""
    for key in ("gt", "gte", "lt", "lte"):
        if key in condition:
            return float(condition[key])
    if "between" in condition:
        return float(condition["between"][1])
    return None
