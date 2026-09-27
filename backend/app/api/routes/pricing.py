from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Query

from app.schemas.pricing import PriceBreakdown
from app.services.pricing import calculate_price_breakdown

router = APIRouter(prefix="/pricing", tags=["pricing"])


@router.get("/preview", response_model=PriceBreakdown)
async def preview(
    base_price: Annotated[Decimal, Query(ge=0, max_digits=10, decimal_places=2)],
    delivery_fee: Annotated[Decimal, Query(ge=0, max_digits=10, decimal_places=2)] = Decimal("0"),
    platform_fee: Annotated[Decimal, Query(ge=0, max_digits=10, decimal_places=2)] = Decimal("0"),
    gst_percent: Annotated[Decimal, Query(ge=0, le=100, max_digits=5, decimal_places=2)] = Decimal("18"),
) -> PriceBreakdown:
    """The all-inclusive price a customer would pay, computed by the same function the store uses."""
    return calculate_price_breakdown(base_price, delivery_fee, platform_fee, gst_percent)
