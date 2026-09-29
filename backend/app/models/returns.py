import enum
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.types import pg_enum, utcnow
from app.models.order import OrderItem


class ReturnReason(enum.StrEnum):
    WRONG_ITEM = "wrong_item"
    COUNTERFEIT = "counterfeit"
    DAMAGED = "damaged"
    WRONG_SIZE = "wrong_size"  # can ask for an exchange to another size
    OTHER = "other"


# Always returnable within the window, even for non-returnable products; they also cost the
# seller trust score when approved.
GUARANTEED_RETURN_REASONS = frozenset({ReturnReason.WRONG_ITEM, ReturnReason.COUNTERFEIT})


class ReturnStatus(enum.StrEnum):
    REQUESTED = "requested"
    APPROVED = "approved"
    REJECTED = "rejected"


class ReturnRequest(Base):
    __tablename__ = "return_requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    # One return request per purchased line.
    order_item_id: Mapped[int] = mapped_column(ForeignKey("order_items.id", ondelete="CASCADE"), unique=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    reason: Mapped[ReturnReason] = mapped_column(pg_enum(ReturnReason, "return_reason"))
    description: Mapped[str] = mapped_column(Text)
    status: Mapped[ReturnStatus] = mapped_column(pg_enum(ReturnStatus, "return_status"), default=ReturnStatus.REQUESTED)
    refund_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    # Wrong size: the size the customer wants instead (stock is reserved when approved).
    exchange_size: Mapped[str | None] = mapped_column(String(20), nullable=True)
    resolution_note: Mapped[str | None] = mapped_column(String(500), nullable=True)
    resolved_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, server_default=func.now())
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    order_item: Mapped[OrderItem] = relationship(lazy="raise")
