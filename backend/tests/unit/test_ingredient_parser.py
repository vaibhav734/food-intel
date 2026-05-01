"""Unit tests for the ingredient parser."""

from __future__ import annotations

from pathlib import Path

import pytest

from food_intel.core.ingredient_parser import (
    _detect_e_number,
    _expand_parenthetical,
    _normalize,
    _split_top_level,
    enrich_product,
    load_catalog,
    parse,
)
from food_intel.core.models import NutritionFacts, Product


CATALOG_PATH = (
    Path(__file__).parent.parent.parent
    / "src" / "food_intel" / "core" / "rules" / "config" / "additives_v1.yaml"
)


@pytest.fixture(scope="module")
def catalog():
    return load_catalog(CATALOG_PATH)


# --------------------------------------------------------------------------
# Tokenization primitives
# --------------------------------------------------------------------------


class TestSplitTopLevel:
    def test_simple_comma_split(self):
        assert _split_top_level("flour, sugar, salt") == ["flour", "sugar", "salt"]

    def test_preserves_parens(self):
        result = _split_top_level("flour (wheat, barley), sugar")
        assert result == ["flour (wheat, barley)", "sugar"]

    def test_handles_semicolons(self):
        assert _split_top_level("a; b; c") == ["a", "b", "c"]

    def test_strips_empty_segments(self):
        assert _split_top_level("a,,b,") == ["a", "b"]

    def test_nested_parens(self):
        # rare but seen on real labels
        result = _split_top_level("emulsifier (lecithin (soy)), oil")
        assert result == ["emulsifier (lecithin (soy))", "oil"]


class TestExpandParenthetical:
    def test_no_parens_passthrough(self):
        assert _expand_parenthetical("sugar") == ["sugar"]

    def test_outer_and_inner(self):
        result = _expand_parenthetical("flour (wheat, barley)")
        assert result == ["flour", "wheat", "barley"]

    def test_only_inner_when_no_outer(self):
        # "(milk, cream)" with nothing in front
        result = _expand_parenthetical("(milk, cream)")
        assert "milk" in result and "cream" in result


class TestNormalize:
    def test_lowercase(self):
        assert _normalize("SUGAR") == "sugar"

    def test_collapse_whitespace(self):
        assert _normalize("  rolled    oats  ") == "rolled oats"

    def test_strip_punctuation(self):
        assert _normalize(".sugar.") == "sugar"


# --------------------------------------------------------------------------
# E-number detection
# --------------------------------------------------------------------------


class TestEnumberDetection:
    def test_basic_e_number(self):
        assert _detect_e_number("E150") == 150

    def test_e_number_with_letter_suffix(self):
        assert _detect_e_number("E150a") == 150

    def test_e_number_with_space(self):
        assert _detect_e_number("E 621") == 621

    def test_ins_prefix(self):
        assert _detect_e_number("INS 160a") == 160

    def test_lowercase_e(self):
        assert _detect_e_number("e160a") == 160

    def test_no_e_number(self):
        assert _detect_e_number("sugar") is None

    def test_does_not_match_bare_numbers(self):
        # "100% rolled oats" should not become E-100
        assert _detect_e_number("100% rolled oats") is None


# --------------------------------------------------------------------------
# Full parse
# --------------------------------------------------------------------------


class TestParse:
    def test_empty_input(self, catalog):
        tokens, flagged = parse("", catalog)
        assert tokens == []
        assert flagged == []

    def test_whitespace_only(self, catalog):
        tokens, flagged = parse("   ", catalog)
        assert tokens == []
        assert flagged == []

    def test_simple_clean_label(self, catalog):
        tokens, flagged = parse("100% rolled oats", catalog)
        assert len(tokens) == 1
        assert tokens[0].normalized == "100% rolled oats" or "rolled oats" in tokens[0].normalized
        assert flagged == []

    def test_e_number_detected(self, catalog):
        tokens, flagged = parse("flour, color (E150a), sugar", catalog)
        # E150a is in the 100-199 range → "color"
        assert "color" in flagged
        e_token = next(t for t in tokens if t.e_number == 150)
        assert e_token.additive_class == "color"

    def test_named_additive_msg(self, catalog):
        tokens, flagged = parse("salt, MSG, water", catalog)
        assert "flavor_enhancer" in flagged

    def test_dedup_classes(self, catalog):
        tokens, flagged = parse("color (E150a), color (E160a)", catalog)
        # Both are in the color range; should appear once
        assert flagged.count("color") == 1

    def test_multiple_classes_in_order(self, catalog):
        tokens, flagged = parse(
            "wheat flour, color (E150d), sodium benzoate, MSG", catalog
        )
        # Insertion order preserved
        assert flagged == ["color", "preservative", "flavor_enhancer"]

    def test_parenthetical_expansion(self, catalog):
        tokens, flagged = parse("flour (wheat, barley), sugar", catalog)
        normalized = [t.normalized for t in tokens]
        assert "wheat" in normalized
        assert "barley" in normalized
        assert "sugar" in normalized

    def test_added_sugars_categorized(self, catalog):
        tokens, _ = parse("wheat flour, sugar, glucose syrup", catalog)
        sugar_token = next(t for t in tokens if t.normalized == "sugar")
        assert "added_sugars" in sugar_token.categories

    def test_oils_categorized(self, catalog):
        tokens, _ = parse("flour, palm oil, salt", catalog)
        palm = next(t for t in tokens if "palm oil" in t.normalized)
        assert "oils_and_fats" in palm.categories


# --------------------------------------------------------------------------
# Integration: enrich_product
# --------------------------------------------------------------------------


class TestEnrichProduct:
    def test_populates_tokens_and_classes(self, catalog):
        product = Product(
            name="test",
            ingredients_raw="wheat flour, sugar, color (E150a), MSG",
        )
        enrich_product(product, catalog)
        assert len(product.ingredient_tokens) >= 4
        assert "color" in product.flagged_additive_classes
        assert "flavor_enhancer" in product.flagged_additive_classes

    def test_idempotent(self, catalog):
        product = Product(name="test", ingredients_raw="sugar, MSG")
        enrich_product(product, catalog)
        first_tokens = list(product.ingredient_tokens)
        first_flags = list(product.flagged_additive_classes)
        enrich_product(product, catalog)
        assert [t.normalized for t in product.ingredient_tokens] == [t.normalized for t in first_tokens]
        assert product.flagged_additive_classes == first_flags

    def test_preserves_manually_set_classes(self, catalog):
        # User pre-tagged a product with "color" — parser shouldn't drop it
        product = Product(
            name="test",
            ingredients_raw="wheat flour, MSG",
            flagged_additive_classes=["color"],
        )
        enrich_product(product, catalog)
        assert "color" in product.flagged_additive_classes
        assert "flavor_enhancer" in product.flagged_additive_classes

    def test_no_raw_ingredients_is_noop(self, catalog):
        product = Product(name="test", nutrition=NutritionFacts(sugar_g=5))
        enrich_product(product, catalog)
        assert product.ingredient_tokens == []
        assert product.flagged_additive_classes == []
