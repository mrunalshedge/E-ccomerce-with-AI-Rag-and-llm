"""Initial schema (Phase 1): pgvector, users, sellers, products

Revision ID: 0001
Revises:
Create Date: 2026-09-26
"""

from collections.abc import Sequence

import pgvector.sqlalchemy
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

user_role = postgresql.ENUM("customer", "seller", "admin", name="user_role", create_type=False)


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    user_role.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("role", user_role, nullable=False),
        sa.Column("preferred_language", sa.String(10), server_default="en", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "sellers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("business_name", sa.String(200), nullable=False),
        sa.Column("contact_email", sa.String(255), nullable=False),
        sa.Column("phone", sa.String(20), nullable=False),
        sa.Column("address", sa.Text(), nullable=False),
        sa.Column("gstin", sa.String(15), nullable=True),
        sa.Column("grievance_officer_name", sa.String(120), nullable=False),
        sa.Column("grievance_officer_email", sa.String(255), nullable=False),
        sa.Column("trust_score", sa.Float(), server_default="100", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("trust_score >= 0 AND trust_score <= 100", name="ck_sellers_trust_score_range"),
        sa.UniqueConstraint("user_id"),
    )

    op.create_table(
        "products",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("seller_id", sa.Integer(), sa.ForeignKey("sellers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("category", sa.String(100), nullable=False),
        sa.Column("base_price", sa.Numeric(10, 2), nullable=False),
        sa.Column("delivery_fee", sa.Numeric(10, 2), server_default="0", nullable=False),
        sa.Column("platform_fee", sa.Numeric(10, 2), server_default="0", nullable=False),
        sa.Column("gst_percent", sa.Numeric(5, 2), server_default="18", nullable=False),
        sa.Column("stock", sa.Integer(), server_default="0", nullable=False),
        sa.Column("is_returnable", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("country_of_origin", sa.String(100), server_default="India", nullable=False),
        sa.Column("embedding", pgvector.sqlalchemy.Vector(384), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("base_price >= 0", name="ck_products_base_price_nonneg"),
        sa.CheckConstraint("delivery_fee >= 0", name="ck_products_delivery_fee_nonneg"),
        sa.CheckConstraint("platform_fee >= 0", name="ck_products_platform_fee_nonneg"),
        sa.CheckConstraint("gst_percent >= 0 AND gst_percent <= 100", name="ck_products_gst_range"),
        sa.CheckConstraint("stock >= 0", name="ck_products_stock_nonneg"),
    )
    op.create_index("ix_products_seller_id", "products", ["seller_id"])
    op.create_index("ix_products_category", "products", ["category"])


def downgrade() -> None:
    op.drop_table("products")
    op.drop_table("sellers")
    op.drop_table("users")
    user_role.drop(op.get_bind(), checkfirst=True)
