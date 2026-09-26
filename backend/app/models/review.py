"""Verified-purchase reviews and cached AI review summaries."""

import enum
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.types import pg_enum, utcnow
from app.models.product import EMBEDDING_DIM
from app.models.user import User


class ReviewStatus(enum.StrEnum):
    PUBLISHED = "published"  # visible and counted in ratings (all honest reviews, good or bad)
    FLAGGED = "flagged"  # looks fake: hidden from ratings until an admin checks it
    REMOVED = "removed"  # removed by an admin (fake or abusive)


class Review(Base):
    __tablename__ = "reviews"
    __table_args__ = (CheckConstraint("rating BETWEEN 1 AND 5", name="ck_reviews_rating_range"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    # The purchase that makes this a verified review; one review per purchased line.
    order_item_id: Mapped[int] = mapped_column(ForeignKey("order_items.id", ondelete="CASCADE"), unique=True)
    rating: Mapped[int] = mapped_column(Integer)
    title: Mapped[str | None] = mapped_column(String(120), nullable=True)
    body: Mapped[str] = mapped_column(Text)
    status: Mapped[ReviewStatus] = mapped_column(pg_enum(ReviewStatus, "review_status"), default=ReviewStatus.PUBLISHED)
    # Fake-review detection: 0–1 score and the machine-readable reasons behind it.
    suspicion_score: Mapped[float] = mapped_column(Float, default=0.0, server_default="0")
    suspicion_reasons: Mapped[list[str]] = mapped_column(JSON, default=list, server_default="[]")
    moderation_note: Mapped[str | None] = mapped_column(String(500), nullable=True)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(EMBEDDING_DIM), nullable=True, deferred=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, server_default=func.now())

    user: Mapped[User] = relationship(lazy="raise")


class ReviewSummary(Base):
    """Cached AI summary per product and language; regenerated when the review count changes."""

    __tablename__ = "review_summaries"
    __table_args__ = (UniqueConstraint("product_id", "language", name="uq_review_summaries_product_language"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"))
    language: Mapped[str] = mapped_column(String(10))
    summary: Mapped[str] = mapped_column(Text)
    review_count: Mapped[int] = mapped_column(Integer)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, server_default=func.now())
