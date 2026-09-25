"""Phase 2: cart, orders (+ status timeline), returns

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-26
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Enum types are created once up front (order_status is shared by two tables).
order_status = postgresql.ENUM("placed", "shipped", "delivered", "cancelled", name="order_status", create_type=False)
payment_method = postgresql.ENUM("upi", "card", "cod", name="payment_method", create_type=False)
payment_status = postgresql.ENUM("pending", "paid", "refunded", "void", name="payment_status", create_type=False)
return_reason = postgresql.ENUM("wrong_item", "counterfeit", "damaged", "other", name="return_reason", create_type=False)
return_status = postgresql.ENUM("requested", "approved", "rejected", name="return_status", create_type=False)
ENUMS = (order_status, payment_method, payment_status, return_reason, return_status)


def upgrade() -> None:
    bind = op.get_bind()
    for enum_type in ENUMS:
        enum_type.create(bind, checkfirst=True)

    op.create_table(
        "cart_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id", ondelete="CASCADE"), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("added_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("quantity > 0", name="ck_cart_items_quantity_positive"),
        sa.UniqueConstraint("user_id", "product_id", name="uq_cart_items_user_product"),
    )
    op.create_index("ix_cart_items_user_id", "cart_items", ["user_id"])

    op.create_table(
        "orders",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("seller_id", sa.Integer(), sa.ForeignKey("sellers.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("status", order_status, nullable=False),
        sa.Column("payment_method", payment_method, nullable=False),
        sa.Column("payment_status", payment_status, nullable=False),
        sa.Column("shipping_address", sa.Text(), nullable=False),
        sa.Column("total_base", sa.Numeric(12, 2), nullable=False),
        sa.Column("total_delivery", sa.Numeric(12, 2), nullable=False),
        sa.Column("total_platform_fee", sa.Numeric(12, 2), nullable=False),
        sa.Column("total_gst", sa.Numeric(12, 2), nullable=False),
        sa.Column("grand_total", sa.Numeric(12, 2), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_orders_user_id", "orders", ["user_id"])
    op.create_index("ix_orders_seller_id", "orders", ["seller_id"])

    op.create_table(
        "order_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("order_id", sa.Integer(), sa.ForeignKey("orders.id", ondelete="CASCADE"), nullable=False),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id", ondelete="SET NULL"), nullable=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("unit_base_price", sa.Numeric(10, 2), nullable=False),
        sa.Column("unit_delivery_fee", sa.Numeric(10, 2), nullable=False),
        sa.Column("unit_platform_fee", sa.Numeric(10, 2), nullable=False),
        sa.Column("gst_percent", sa.Numeric(5, 2), nullable=False),
        sa.Column("unit_gst_amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("unit_final_price", sa.Numeric(10, 2), nullable=False),
        sa.Column("line_total", sa.Numeric(12, 2), nullable=False),
        sa.Column("is_returnable", sa.Boolean(), nullable=False),
    )
    op.create_index("ix_order_items_order_id", "order_items", ["order_id"])

    op.create_table(
        "order_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("order_id", sa.Integer(), sa.ForeignKey("orders.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", order_status, nullable=False),
        sa.Column("note", sa.String(500), nullable=True),
        sa.Column("actor_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_order_events_order_id", "order_events", ["order_id"])

    op.create_table(
        "return_requests",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "order_item_id", sa.Integer(), sa.ForeignKey("order_items.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("reason", return_reason, nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("status", return_status, nullable=False),
        sa.Column("refund_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("resolution_note", sa.String(500), nullable=True),
        sa.Column("resolved_by_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("order_item_id"),
    )
    op.create_index("ix_return_requests_user_id", "return_requests", ["user_id"])


def downgrade() -> None:
    op.drop_table("return_requests")
    op.drop_table("order_events")
    op.drop_table("order_items")
    op.drop_table("orders")
    op.drop_table("cart_items")
    bind = op.get_bind()
    for enum_type in reversed(ENUMS):
        enum_type.drop(bind, checkfirst=True)
