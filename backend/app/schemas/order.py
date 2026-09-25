from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.order import OrderStatus, PaymentMethod, PaymentStatus
from app.schemas.pricing import OrderTotals, PriceBreakdown


class CheckoutRequest(BaseModel):
    # Required, no default: the payment method is always the customer's explicit choice.
    payment_method: PaymentMethod
    shipping_address: str = Field(min_length=10, max_length=500)
    expected_total: Decimal = Field(
        ge=0,
        max_digits=12,
        decimal_places=2,
        description="The grand total the customer saw. Checkout is refused if the real total differs.",
    )


class SellerSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    business_name: str


class OrderItemRead(BaseModel):
    id: int
    product_id: int | None
    title: str
    quantity: int
    unit_price: PriceBreakdown
    line_total: Decimal
    is_returnable: bool


class OrderEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    status: OrderStatus
    note: str | None
    created_at: datetime


class OrderRead(BaseModel):
    id: int
    status: OrderStatus
    payment_method: PaymentMethod
    payment_status: PaymentStatus
    shipping_address: str
    seller: SellerSummary
    items: list[OrderItemRead]
    totals: OrderTotals
    timeline: list[OrderEventRead]
    created_at: datetime
    delivered_at: datetime | None


class CheckoutResponse(BaseModel):
    """Checkout splits the cart into one order per seller."""

    orders: list[OrderRead]
    grand_total: Decimal


class OrderStatusUpdate(BaseModel):
    status: OrderStatus
    note: str | None = Field(default=None, max_length=500)
