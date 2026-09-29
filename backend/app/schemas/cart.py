from decimal import Decimal

from pydantic import BaseModel, Field

from app.core.policies import MAX_QUANTITY_PER_ITEM
from app.schemas.pricing import OrderTotals, PriceBreakdown


class CartItemAdd(BaseModel):
    product_id: int = Field(gt=0)
    quantity: int = Field(default=1, ge=1, le=MAX_QUANTITY_PER_ITEM)
    size: str | None = Field(default=None, min_length=1, max_length=20)  # required for sized products


class CartItemUpdate(BaseModel):
    quantity: int = Field(ge=1, le=MAX_QUANTITY_PER_ITEM)


class CartLine(BaseModel):
    product_id: int
    title: str
    category: str
    image_url: str | None
    seller_id: int
    seller_name: str
    size: str | None
    quantity: int
    available_stock: int
    unit_price: PriceBreakdown
    line_total: Decimal


class CartRead(BaseModel):
    items: list[CartLine]
    totals: OrderTotals
