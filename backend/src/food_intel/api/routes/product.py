"""GET /product/{barcode} — look up by barcode and analyze."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Path

from food_intel.adapters.product_lookup.base import ProductNotFoundError
from food_intel.api.deps import get_analysis_service
from food_intel.api.schemas import AnalyzeResponse
from food_intel.services.analyze import AnalysisService

router = APIRouter(tags=["product"])


@router.get(
    "/product/{barcode}",
    response_model=AnalyzeResponse,
    responses={
        404: {"description": "No product found for the supplied barcode"},
        503: {"description": "Product lookup is not configured"},
    },
)
def get_product(
    barcode: str = Path(..., min_length=4, max_length=32, pattern=r"^\d+$"),
    service: AnalysisService = Depends(get_analysis_service),
) -> AnalyzeResponse:
    """Look up a product by barcode (via the configured lookup) and analyze it."""
    if service.product_lookup is None:
        raise HTTPException(
            status_code=503,
            detail="Product lookup is not enabled in this deployment.",
        )
    try:
        result = service.analyze_by_barcode(barcode)
    except ProductNotFoundError:
        raise HTTPException(status_code=404, detail=f"Barcode {barcode} not found")
    return AnalyzeResponse.from_analysis(result)
