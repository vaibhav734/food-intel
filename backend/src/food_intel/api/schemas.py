"""
API schemas — request and response shapes for the HTTP layer.

These are deliberately separate from core domain models. The API contract
is a public surface versioned independently of internal models.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

from food_intel.core.models import (
    Confidence,
    Product,
    SourceType,
    Verdict,
)
from food_intel.services.analyze import AnalysisResult


# ===========================================================================
# Requests
# ===========================================================================


class NutritionInput(BaseModel):
    """Per-100g nutrition values supplied in an analyze request."""
    calories_kcal: Optional[float] = Field(None, ge=0)
    sugar_g: Optional[float] = Field(None, ge=0)
    saturated_fat_g: Optional[float] = Field(None, ge=0)
    sodium_mg: Optional[float] = Field(None, ge=0)
    protein_g: Optional[float] = Field(None, ge=0)
    fiber_g: Optional[float] = Field(None, ge=0)
    serving_size_g: Optional[float] = Field(None, gt=0)


class AnalyzeRequest(BaseModel):
    """POST /analyze body."""
    name: str = Field(..., min_length=1, max_length=200)
    barcode: Optional[str] = Field(None, max_length=32)
    nutrition: NutritionInput = Field(default_factory=NutritionInput)
    ingredients_raw: Optional[str] = Field(None, max_length=5000)
    nova_class: Optional[int] = Field(None, ge=1, le=4)
    product_type: str = Field("food", pattern="^(food|baby_food|cosmetic)$")
    min_age_months: Optional[int] = Field(None, ge=0)
    max_age_months: Optional[int] = Field(None, ge=0)


# ===========================================================================
# Responses
# ===========================================================================


class SourceOut(BaseModel):
    org: str
    type: SourceType
    doc: Optional[str] = None


class ReasonOut(BaseModel):
    rule_id: str
    text: str
    delta: float
    source: SourceOut
    observed_value: Optional[float] = None
    threshold: Optional[float] = None


class AgeSafetyOut(BaseModel):
    min_age_months: Optional[int] = None
    max_age_months: Optional[int] = None
    label: str
    safe: bool


class ScoringOut(BaseModel):
    score: int
    raw_score: float
    verdict: Verdict
    reasons: list[ReasonOut]
    confidence: Confidence
    completeness: float
    missing_fields: list[str]
    rules_version: str
    age_safety: Optional[AgeSafetyOut] = None
    data_unavailable: bool = False


class AnalyzeResponse(BaseModel):
    """Full analyze response: deterministic facts + explanation."""
    product_name: str
    barcode: Optional[str] = None
    scoring: ScoringOut
    explanation: str
    nutrition: NutritionInput = Field(default_factory=NutritionInput)

    @classmethod
    def from_analysis(cls, result: AnalysisResult) -> "AnalyzeResponse":
        n = result.product.nutrition
        return cls(
            product_name=result.product.name,
            barcode=result.product.barcode,
            nutrition=NutritionInput(
                calories_kcal=n.calories_kcal,
                sugar_g=n.sugar_g,
                saturated_fat_g=n.saturated_fat_g,
                sodium_mg=n.sodium_mg,
                protein_g=n.protein_g,
                fiber_g=n.fiber_g,
                serving_size_g=n.serving_size_g,
            ),
            scoring=ScoringOut(
                score=result.scoring.score,
                raw_score=result.scoring.raw_score,
                verdict=result.scoring.verdict,
                reasons=[
                    ReasonOut(
                        rule_id=h.rule_id,
                        text=h.text,
                        delta=h.delta,
                        source=SourceOut(
                            org=h.source.org,
                            type=h.source.type,
                            doc=h.source.doc,
                        ),
                        observed_value=h.observed_value,
                        threshold=h.threshold,
                    )
                    for h in result.scoring.reasons
                ],
                confidence=result.scoring.confidence,
                completeness=result.scoring.completeness,
                missing_fields=result.scoring.missing_fields,
                rules_version=result.scoring.rules_version,
                age_safety=(
                    AgeSafetyOut(
                        min_age_months=result.scoring.age_safety.min_age_months,
                        max_age_months=result.scoring.age_safety.max_age_months,
                        label=result.scoring.age_safety.label,
                        safe=result.scoring.age_safety.safe,
                    )
                    if result.scoring.age_safety else None
                ),
                data_unavailable=result.scoring.data_unavailable,
            ),
            explanation=result.explanation,
        )


def request_to_product(req: AnalyzeRequest) -> Product:
    """Convert an incoming API request into a core Product."""
    from food_intel.core.models import NutritionFacts
    return Product(
        name=req.name,
        barcode=req.barcode,
        nutrition=NutritionFacts(
            calories_kcal=req.nutrition.calories_kcal,
            sugar_g=req.nutrition.sugar_g,
            saturated_fat_g=req.nutrition.saturated_fat_g,
            sodium_mg=req.nutrition.sodium_mg,
            protein_g=req.nutrition.protein_g,
            fiber_g=req.nutrition.fiber_g,
            serving_size_g=req.nutrition.serving_size_g,
        ),
        ingredients_raw=req.ingredients_raw,
        nova_class=req.nova_class,
        product_type=req.product_type,
        min_age_months=req.min_age_months,
        max_age_months=req.max_age_months,
    )


class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None
