"""
Ingredient parser.

Takes the raw ingredient string from a product label and produces:
  - a list of IngredientTokens, each classified
  - the deduplicated list of flagged additive classes for the rules engine

Real-world label strings are messy. The parser handles:
  - comma and semicolon separators
  - parenthetical sub-ingredients ("flour (wheat, barley)")
  - E-numbers in various formats (E160a, E 160a, INS 160a, "160a")
  - case insensitivity
  - punctuation noise

What it does NOT handle (yet):
  - Multi-language labels — assumes English. International expansion is a
    separate problem that needs per-language additive name lists.
  - Allergen extraction — a separate concern from scoring; would go in its
    own module.
  - Quantity parsing ("12% sugar") — not needed for current rules.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

import yaml

from food_intel.core.models import IngredientToken


# E-number pattern: matches "E150a", "E 150", "INS 621", standalone "160a"
# is intentionally NOT matched — too many false positives with real numbers.
E_NUMBER_RE = re.compile(
    r"\b(?:E|INS)\s?(\d{3})([a-z]?)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class AdditiveCatalog:
    """Loaded additives configuration."""
    version: str
    e_number_ranges: list[dict[str, Any]]
    named_additives: list[dict[str, str]]
    ingredient_categories: dict[str, list[str]]


def load_catalog(path: Path) -> AdditiveCatalog:
    """Load and validate the additives YAML."""
    with path.open() as f:
        raw = yaml.safe_load(f)
    return AdditiveCatalog(
        version=raw["version"],
        e_number_ranges=raw.get("e_number_ranges", []),
        named_additives=raw.get("named_additives", []),
        ingredient_categories=raw.get("ingredient_categories", {}),
    )


# ---------------------------------------------------------------------------
# Tokenization
# ---------------------------------------------------------------------------

def _split_top_level(text: str) -> list[str]:
    """
    Split on commas and semicolons, but only at top level — preserving
    parenthetical groups as single tokens. So:
        "flour (wheat, barley), sugar, salt"
    becomes:
        ["flour (wheat, barley)", "sugar", "salt"]
    """
    tokens: list[str] = []
    depth = 0
    current: list[str] = []

    for char in text:
        if char in "([":
            depth += 1
            current.append(char)
        elif char in ")]":
            depth = max(0, depth - 1)
            current.append(char)
        elif char in ",;" and depth == 0:
            tokens.append("".join(current).strip())
            current = []
        else:
            current.append(char)

    if current:
        tokens.append("".join(current).strip())

    return [t for t in tokens if t]


def _expand_parenthetical(token: str) -> list[str]:
    """
    Flatten one level of parentheses. "flour (wheat, barley)" becomes
    ["flour", "wheat", "barley"]. The outer name and inner ingredients
    are all surfaced — both can be relevant for classification.
    """
    if "(" not in token:
        return [token]

    paren_start = token.index("(")
    outer = token[:paren_start].strip()
    inner_match = re.search(r"\(([^()]*)\)", token)
    if not inner_match:
        return [outer] if outer else [token]

    inner_parts = [p.strip() for p in re.split(r"[,;]", inner_match.group(1)) if p.strip()]
    return ([outer] if outer else []) + inner_parts


def _normalize(text: str) -> str:
    """Lowercase, strip surrounding punctuation/whitespace, collapse runs of spaces."""
    cleaned = re.sub(r"\s+", " ", text).strip().lower()
    # Strip leading/trailing punctuation but keep internal hyphens
    cleaned = re.sub(r"^[^\w]+|[^\w\)]+$", "", cleaned)
    return cleaned


# ---------------------------------------------------------------------------
# Classification
# ---------------------------------------------------------------------------

def _detect_e_number(text: str) -> Optional[int]:
    """Pull an E-number out of a token if present. Returns the integer part only."""
    match = E_NUMBER_RE.search(text)
    if not match:
        return None
    try:
        return int(match.group(1))
    except ValueError:
        return None


def _e_number_to_class(e_number: int, catalog: AdditiveCatalog) -> Optional[str]:
    """Look up which class an E-number falls into."""
    for r in catalog.e_number_ranges:
        if r["from"] <= e_number <= r["to"]:
            return r["class"]
    return None


def _named_additive_class(normalized: str, catalog: AdditiveCatalog) -> Optional[str]:
    """Match against the named additives list (substring, case-insensitive)."""
    for entry in catalog.named_additives:
        if entry["match"] in normalized:
            return entry["class"]
    return None


def _categorize(normalized: str, catalog: AdditiveCatalog) -> list[str]:
    """Return all ingredient_categories matching this token."""
    found = []
    for category, terms in catalog.ingredient_categories.items():
        for term in terms:
            if term in normalized:
                found.append(category)
                break  # one match per category is enough
    return found


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def parse(raw: str, catalog: AdditiveCatalog) -> tuple[list[IngredientToken], list[str]]:
    """
    Parse a raw ingredient string.

    Returns (tokens, flagged_classes) where flagged_classes is the
    deduplicated list of additive classes that the rules engine consumes.
    """
    if not raw or not raw.strip():
        return [], []

    raw_tokens = _split_top_level(raw)
    expanded: list[str] = []
    for t in raw_tokens:
        expanded.extend(_expand_parenthetical(t))

    tokens: list[IngredientToken] = []
    seen_classes: list[str] = []  # preserve order, but dedupe

    for original in expanded:
        normalized = _normalize(original)
        if not normalized:
            continue

        e_number = _detect_e_number(original)
        additive_class = None
        if e_number is not None:
            additive_class = _e_number_to_class(e_number, catalog)
        if additive_class is None:
            additive_class = _named_additive_class(normalized, catalog)

        categories = _categorize(normalized, catalog)

        token = IngredientToken(
            text=original.strip(),
            normalized=normalized,
            e_number=e_number,
            additive_class=additive_class,
            categories=categories,
        )
        tokens.append(token)

        if additive_class and additive_class not in seen_classes:
            seen_classes.append(additive_class)

    return tokens, seen_classes


def enrich_product(product, catalog: AdditiveCatalog) -> None:
    """
    Run the parser against product.ingredients_raw and populate the parsed
    fields in place. Idempotent — calling twice yields the same result.

    Caller responsibility: only call this once during the analyze pipeline,
    typically just before invoking the rules engine.
    """
    if not product.ingredients_raw:
        return
    tokens, flagged = parse(product.ingredients_raw, catalog)
    product.ingredient_tokens = tokens
    product.ingredients_parsed = [t.normalized for t in tokens]
    # Don't clobber manually-set classes — merge instead, preserving order
    existing = list(product.flagged_additive_classes)
    for cls in flagged:
        if cls not in existing:
            existing.append(cls)
    product.flagged_additive_classes = existing
