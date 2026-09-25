from datetime import UTC, datetime

from sqlalchemy import CheckConstraint, DateTime, Float, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Seller(Base):
    """Seller profile. Its public fields form the seller info card shown on every listing
    (Consumer Protection (E-Commerce) Rules 2020: legal name, address, contact, GSTIN,
    grievance officer)."""

    __tablename__ = "sellers"
    __table_args__ = (
        CheckConstraint("trust_score >= 0 AND trust_score <= 100", name="ck_sellers_trust_score_range"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    business_name: Mapped[str] = mapped_column(String(200))
    contact_email: Mapped[str] = mapped_column(String(255))
    phone: Mapped[str] = mapped_column(String(20))
    address: Mapped[str] = mapped_column(Text)
    # Optional so non-Indian sellers can onboard later.
    gstin: Mapped[str | None] = mapped_column(String(15), nullable=True)
    grievance_officer_name: Mapped[str] = mapped_column(String(120))
    grievance_officer_email: Mapped[str] = mapped_column(String(255))
    # 0–100; starts at 100 and will drop on wrong/fake-item returns and complaints (later phases).
    trust_score: Mapped[float] = mapped_column(Float, default=100.0, server_default="100")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), server_default=func.now()
    )
