from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.types import utcnow
from app.models.product import Product


class CartItem(Base):
    """One product line in a customer's cart. Rows are only ever created by the customer's own
    action (no auto-added or pre-ticked items)."""

    __tablename__ = "cart_items"
    __table_args__ = (
        # One line per product *and size*; NULLS NOT DISTINCT so unsized products still get one line.
        UniqueConstraint(
            "user_id", "product_id", "size", name="uq_cart_items_user_product_size", postgresql_nulls_not_distinct=True
        ),
        CheckConstraint("quantity > 0", name="ck_cart_items_quantity_positive"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"))
    size: Mapped[str | None] = mapped_column(String(20), nullable=True)
    quantity: Mapped[int] = mapped_column(Integer)
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, server_default=func.now())

    product: Mapped[Product] = relationship(lazy="raise")
