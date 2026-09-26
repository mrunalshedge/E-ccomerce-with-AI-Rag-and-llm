from datetime import UTC, datetime
from decimal import Decimal

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.seller import Seller

# Matches sentence-transformers/all-MiniLM-L6-v2 (Phase 3).
EMBEDDING_DIM = 384


class Product(Base):
    __tablename__ = "products"
    __table_args__ = (
        CheckConstraint("base_price >= 0", name="ck_products_base_price_nonneg"),
        CheckConstraint("delivery_fee >= 0", name="ck_products_delivery_fee_nonneg"),
        CheckConstraint("platform_fee >= 0", name="ck_products_platform_fee_nonneg"),
        CheckConstraint("gst_percent >= 0 AND gst_percent <= 100", name="ck_products_gst_range"),
        CheckConstraint("stock >= 0", name="ck_products_stock_nonneg"),
        # Approximate nearest-neighbour index for cosine similarity search (pgvector HNSW).
        Index(
            "ix_products_embedding_hnsw",
            "embedding",
            postgresql_using="hnsw",
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    seller_id: Mapped[int] = mapped_column(ForeignKey("sellers.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)
    # Stored lowercase (normalised by the schema) so filtering can use the plain index.
    category: Mapped[str] = mapped_column(String(100), index=True)
    base_price: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    delivery_fee: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0"), server_default="0")
    platform_fee: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0"), server_default="0")
    gst_percent: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("18"), server_default="18")
    stock: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    is_returnable: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    country_of_origin: Mapped[str] = mapped_column(String(100), default="India", server_default="India")
    image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    # Deferred: never loaded unless explicitly requested (it's large and not part of responses).
    embedding: Mapped[list[float] | None] = mapped_column(Vector(EMBEDDING_DIM), nullable=True, deferred=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), server_default=func.now()
    )

    # lazy="raise": async sessions can't lazy-load, so force explicit selectinload().
    seller: Mapped[Seller] = relationship(lazy="raise")
