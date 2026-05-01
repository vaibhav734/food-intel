"""GET /product/prefill/{barcode} — fetch raw product data for form pre-filling."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Path
from pydantic import BaseModel

from food_intel.api.deps import get_product_lookup
from food_intel.adapters.product_lookup.base import ProductLookup

router = APIRouter(tags=["prefill"])


class ProductPrefill(BaseModel):
    name: str
    barcode: str
    calories_kcal: Optional[float] = None
    sugar_g: Optional[float] = None
    saturated_fat_g: Optional[float] = None
    sodium_mg: Optional[float] = None
    protein_g: Optional[float] = None
    fiber_g: Optional[float] = None
    serving_size_g: Optional[float] = None
    ingredients_raw: Optional[str] = None
    nova_class: Optional[int] = None
    product_type: str = "food"


@router.get(
    "/product/prefill/{barcode}",
    response_model=ProductPrefill,
    responses={
        404: {"description": "Product not found"},
        503: {"description": "Product lookup not configured"},
    },
)
def prefill_product(
    barcode: str = Path(..., min_length=4, max_length=32, pattern=r"^\d+$"),
    lookup: Optional[ProductLookup] = Depends(get_product_lookup),
) -> ProductPrefill:
    """Return raw product data from Open Food Facts for form pre-filling."""
    if lookup is None:
        raise HTTPException(status_code=503, detail="Product lookup not enabled.")
    product = lookup.get_by_barcode(barcode)
    if product is None:
        raise HTTPException(status_code=404, detail=f"Barcode {barcode} not found")
    n = product.nutrition
    return ProductPrefill(
        name=product.name,
        barcode=barcode,
        calories_kcal=n.calories_kcal,
        sugar_g=n.sugar_g,
        saturated_fat_g=n.saturated_fat_g,
        sodium_mg=n.sodium_mg,
        protein_g=n.protein_g,
        fiber_g=n.fiber_g,
        serving_size_g=n.serving_size_g,
        ingredients_raw=product.ingredients_raw,
        nova_class=product.nova_class,
        product_type=product.product_type,
    )
