"""POST /analyze — score a product from supplied data."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from typing import Optional

from food_intel.api.deps import get_analysis_service, get_product_lookup
from food_intel.adapters.product_lookup.base import ProductLookup
from food_intel.api.schemas import (
    AnalyzeRequest,
    AnalyzeResponse,
    request_to_product,
)
from food_intel.services.analyze import AnalysisService

router = APIRouter(tags=["analyze"])


def _nutrition_is_empty(req: AnalyzeRequest) -> bool:
    n = req.nutrition
    return all(v is None for v in [
        n.calories_kcal, n.sugar_g, n.saturated_fat_g,
        n.sodium_mg, n.protein_g, n.fiber_g,
    ])


@router.post("/analyze", response_model=AnalyzeResponse)
def analyze(
    request: AnalyzeRequest,
    service: AnalysisService = Depends(get_analysis_service),
    lookup: Optional[ProductLookup] = Depends(get_product_lookup),
) -> AnalyzeResponse:
    """
    Score a product. If a barcode is supplied and nutrition is empty,
    auto-enriches from the local product DB before scoring.
    """
    # Auto-enrich: if barcode given but no nutrition, look up DB first
    if request.barcode and _nutrition_is_empty(request) and lookup is not None:
        db_product = lookup.get_by_barcode(request.barcode)
        if db_product is not None:
            from food_intel.api.schemas import NutritionInput
            n = db_product.nutrition
            request = request.model_copy(update={
                "name": request.name or db_product.name,
                "nutrition": NutritionInput(
                    calories_kcal=n.calories_kcal,
                    sugar_g=n.sugar_g,
                    saturated_fat_g=n.saturated_fat_g,
                    sodium_mg=n.sodium_mg,
                    protein_g=n.protein_g,
                    fiber_g=n.fiber_g,
                    serving_size_g=n.serving_size_g,
                ),
                "ingredients_raw": request.ingredients_raw or db_product.ingredients_raw,
                "nova_class": request.nova_class or db_product.nova_class,
                "product_type": request.product_type or db_product.product_type,
            })

    product = request_to_product(request)
    result = service.analyze_product(product)
    return AnalyzeResponse.from_analysis(result)
