"""
Rule data structures.

Rules are loaded from YAML at startup into these dataclasses. The engine
(see engine.py) iterates over them to produce RuleHits.

Rules are intentionally simple — a condition + a delta + a source. Anything
more complex (e.g. cross-nutrient logic) should compose multiple rules
rather than embedding logic in a single rule definition.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from food_intel.core.models import Source, SourceType


@dataclass(frozen=True)
class Rule:
    """
    A single rule loaded from the YAML config.

    Exactly one of:
      - `penalty` (negative)
      - `bonus` (positive)
      - `per_unit_penalty` (for count-based rules like additives)
    will be set.
    """
    id: str
    text: str
    source: Source
    condition: dict[str, Any]

    # Targets exactly one of these:
    nutrient: Optional[str] = None     # field on NutritionFacts
    field: Optional[str] = None        # field on Product

    # Deltas — exactly one of these is set per rule:
    penalty: Optional[float] = None
    bonus: Optional[float] = None
    per_unit_penalty: Optional[float] = None
    cap: Optional[float] = None        # paired with per_unit_penalty

    # Optional: linear interpolation between thresholds
    interpolate: Optional[dict[str, float]] = None

    @property
    def delta(self) -> float:
        """The signed contribution if the rule fires at full strength."""
        if self.penalty is not None:
            return self.penalty
        if self.bonus is not None:
            return self.bonus
        if self.per_unit_penalty is not None:
            return self.per_unit_penalty
        raise ValueError(f"Rule {self.id} has no delta defined")


def parse_source(raw: dict[str, Any]) -> Source:
    """Convert a YAML source dict into a Source dataclass."""
    return Source(
        org=raw["org"],
        type=SourceType(raw.get("type", "guideline")),
        doc=raw.get("doc"),
    )


def parse_rule(raw: dict[str, Any]) -> Rule:
    """Convert a YAML rule dict into a Rule dataclass with validation."""
    # Validate exactly one delta is specified
    delta_keys = ["penalty", "bonus", "per_unit_penalty"]
    present = [k for k in delta_keys if k in raw]
    if len(present) != 1:
        raise ValueError(
            f"Rule {raw.get('id')!r} must have exactly one of {delta_keys}, "
            f"got {present}"
        )

    # Validate exactly one target (nutrient OR field)
    if ("nutrient" in raw) == ("field" in raw):
        raise ValueError(
            f"Rule {raw.get('id')!r} must specify exactly one of "
            f"'nutrient' or 'field'"
        )

    return Rule(
        id=raw["id"],
        text=raw["text"],
        source=parse_source(raw["source"]),
        condition=raw["condition"],
        nutrient=raw.get("nutrient"),
        field=raw.get("field"),
        penalty=raw.get("penalty"),
        bonus=raw.get("bonus"),
        per_unit_penalty=raw.get("per_unit_penalty"),
        cap=raw.get("cap"),
        interpolate=raw.get("interpolate"),
    )
