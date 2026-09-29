"""Orders. Checkout creates one order per seller (like a shipment), so each seller manages the
status of only their own order. Prices are snapshotted at purchase time and never recalculated."""

import enum
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.types import pg_enum, utcnow
from app.models.seller import Seller


class OrderStatus(enum.StrEnum):
    PLACED = "placed"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


class PaymentMethod(enum.StrEnum):
    UPI = "upi"
    CARD = "card"
    COD = "cod"


class PaymentStatus(enum.StrEnum):
    PENDING = "pending"  # COD, not yet collected
    PAID = "paid"
    REFUNDED = "refunded"  # prepaid order cancelled
    VOID = "void"  # COD order cancelled: nothing was ever collected


# One shared enum object: used by both orders.status and order_events.status.
ORDER_STATUS_ENUM = pg_enum(OrderStatus, "order_status")


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    seller_id: Mapped[int] = mapped_column(ForeignKey("sellers.id", ondelete="RESTRICT"), index=True)
    status: Mapped[OrderStatus] = mapped_column(ORDER_STATUS_ENUM, default=OrderStatus.PLACED)
    payment_method: Mapped[PaymentMethod] = mapped_column(pg_enum(PaymentMethod, "payment_method"))
    payment_status: Mapped[PaymentStatus] = mapped_column(pg_enum(PaymentStatus, "payment_status"))
    shipping_address: Mapped[str] = mapped_column(Text)
    total_base: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    total_delivery: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    total_platform_fee: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    total_gst: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    grand_total: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, server_default=func.now())
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    seller: Mapped[Seller] = relationship(lazy="raise")
    items: Mapped[list["OrderItem"]] = relationship(
        back_populates="order", lazy="raise", cascade="all, delete-orphan", order_by="OrderItem.id"
    )
    events: Mapped[list["OrderEvent"]] = relationship(
        lazy="raise", cascade="all, delete-orphan", order_by="OrderEvent.id"
    )


class OrderItem(Base):
    """A purchased line with its unit price breakdown frozen at checkout."""

    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), index=True)
    # Nullable: the order history must survive the product being deleted later.
    product_id: Mapped[int | None] = mapped_column(ForeignKey("products.id", ondelete="SET NULL"), nullable=True)
    title: Mapped[str] = mapped_column(String(200))
    size: Mapped[str | None] = mapped_column(String(20), nullable=True)
    quantity: Mapped[int] = mapped_column(Integer)
    unit_base_price: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    unit_delivery_fee: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    unit_platform_fee: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    gst_percent: Mapped[Decimal] = mapped_column(Numeric(5, 2))
    unit_gst_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    unit_final_price: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    line_total: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    is_returnable: Mapped[bool] = mapped_column(Boolean)

    order: Mapped[Order] = relationship(back_populates="items", lazy="raise")


class OrderEvent(Base):
    """One entry in an order's status timeline (placed → shipped → delivered / cancelled)."""

    __tablename__ = "order_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), index=True)
    status: Mapped[OrderStatus] = mapped_column(ORDER_STATUS_ENUM)
    note: Mapped[str | None] = mapped_column(String(500), nullable=True)
    actor_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, server_default=func.now())
