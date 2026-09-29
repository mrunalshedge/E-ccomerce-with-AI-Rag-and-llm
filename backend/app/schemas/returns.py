from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field

from app.models.returns import ReturnReason, ReturnStatus


class ReturnCreate(BaseModel):
    order_item_id: int = Field(gt=0)
    reason: ReturnReason
    description: str = Field(min_length=10, max_length=2000)
    # Only with reason "wrong_size": swap for this size instead of a refund.
    exchange_size: str | None = Field(default=None, min_length=1, max_length=20)


class ReturnRead(BaseModel):
    id: int
    order_id: int
    order_item_id: int
    product_title: str
    size: str | None  # the size that was bought
    reason: ReturnReason
    exchange_size: str | None  # set when the customer asked for another size instead of a refund
    description: str
    status: ReturnStatus
    refund_amount: Decimal
    resolution_note: str | None
    created_at: datetime
    resolved_at: datetime | None


class ReturnResolve(BaseModel):
    decision: Literal["approve", "reject"]
    note: str = Field(min_length=3, max_length=500)
