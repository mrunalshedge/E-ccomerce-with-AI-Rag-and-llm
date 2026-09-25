from decimal import Decimal

from pydantic import BaseModel, Field


class PriceBreakdown(BaseModel):
    """All-inclusive price shown up-front (no drip pricing). Lines always sum to ``final_price``."""

    base_price: Decimal
    delivery_fee: Decimal
    platform_fee: Decimal
    taxable_value: Decimal = Field(description="base_price + delivery_fee + platform_fee")
    gst_percent: Decimal
    gst_amount: Decimal
    final_price: Decimal = Field(description="What the customer pays. Nothing is added at checkout.")
    currency: str = "INR"
