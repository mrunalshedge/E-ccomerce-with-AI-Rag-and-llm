"""Customer grievances (complaints) with a status timeline.

Consumer Protection (E-Commerce) Rules 2020: acknowledge within 48 hours, resolve within one
month. AI triage acknowledges instantly and answers simple information requests itself; anything
needing action goes to a person (the grievance officer / admin team).
"""

import enum
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.types import pg_enum, utcnow


class GrievanceCategory(enum.StrEnum):
    DELIVERY = "delivery"  # late, not delivered, where is my order
    WRONG_OR_FAKE_ITEM = "wrong_or_fake_item"
    DAMAGED = "damaged"
    REFUND = "refund"
    PAYMENT = "payment"  # charged twice, money deducted but no order
    SELLER = "seller"  # seller behaviour, misleading listing
    ACCOUNT = "account"
    OTHER = "other"


class GrievancePriority(enum.StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class GrievanceStatus(enum.StrEnum):
    OPEN = "open"  # waiting for the team
    IN_PROGRESS = "in_progress"  # a team member is on it
    AI_RESOLVED = "ai_resolved"  # answered automatically; the customer can reopen
    RESOLVED = "resolved"  # closed by the team


class GrievanceActor(enum.StrEnum):
    CUSTOMER = "customer"
    AI = "ai"
    ADMIN = "admin"


GRIEVANCE_STATUS_ENUM = pg_enum(GrievanceStatus, "grievance_status")


class Grievance(Base):
    __tablename__ = "grievances"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    order_id: Mapped[int | None] = mapped_column(ForeignKey("orders.id", ondelete="SET NULL"), nullable=True)
    subject: Mapped[str] = mapped_column(String(150))
    description: Mapped[str] = mapped_column(Text)
    language: Mapped[str] = mapped_column(String(10), default="en", server_default="en")
    category: Mapped[GrievanceCategory] = mapped_column(pg_enum(GrievanceCategory, "grievance_category"))
    priority: Mapped[GrievancePriority] = mapped_column(pg_enum(GrievancePriority, "grievance_priority"))
    status: Mapped[GrievanceStatus] = mapped_column(GRIEVANCE_STATUS_ENUM, default=GrievanceStatus.OPEN)
    ai_summary: Mapped[str | None] = mapped_column(String(300), nullable=True)  # one line for the team
    ai_reply: Mapped[str | None] = mapped_column(Text, nullable=True)  # shown to the customer
    triaged_by: Mapped[str] = mapped_column(String(20), default="rules")  # "ai" or "rules" (fallback)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, server_default=func.now())
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolve_by: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    events: Mapped[list["GrievanceEvent"]] = relationship(
        lazy="raise", cascade="all, delete-orphan", order_by="GrievanceEvent.id"
    )


class GrievanceEvent(Base):
    """Timeline entry: a status change or a comment, by the customer, the AI or the team."""

    __tablename__ = "grievance_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    grievance_id: Mapped[int] = mapped_column(ForeignKey("grievances.id", ondelete="CASCADE"), index=True)
    status: Mapped[GrievanceStatus] = mapped_column(GRIEVANCE_STATUS_ENUM)  # status after this event
    actor: Mapped[GrievanceActor] = mapped_column(pg_enum(GrievanceActor, "grievance_actor"))
    actor_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    note: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, server_default=func.now())
