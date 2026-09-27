from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models.grievance import GrievanceActor, GrievanceCategory, GrievancePriority, GrievanceStatus


class GrievanceCreate(BaseModel):
    order_id: int | None = Field(default=None, gt=0)
    subject: str = Field(min_length=5, max_length=150)
    description: str = Field(min_length=10, max_length=3000)
    language: Literal["en", "hi", "mr"] = "en"


class GrievanceComment(BaseModel):
    message: str = Field(min_length=2, max_length=2000)


class GrievanceAdminUpdate(BaseModel):
    status: Literal["in_progress", "resolved"]
    note: str = Field(min_length=3, max_length=2000)


class GrievanceEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    status: GrievanceStatus
    actor: GrievanceActor
    note: str
    created_at: datetime


class GrievanceRead(BaseModel):
    id: int
    order_id: int | None
    subject: str
    description: str
    category: GrievanceCategory
    priority: GrievancePriority
    status: GrievanceStatus
    ai_reply: str | None
    created_at: datetime
    acknowledged_at: datetime | None
    resolve_by: datetime
    resolved_at: datetime | None
    overdue: bool
    can_reopen: bool
    timeline: list[GrievanceEventRead]


class AdminGrievanceRead(GrievanceRead):
    customer_name: str
    customer_email: str
    ai_summary: str | None
    triaged_by: str


class AdminOverview(BaseModel):
    open_grievances: int
    urgent_or_high: int
    overdue_grievances: int
    flagged_reviews: int
    pending_returns: int
    orders_today: int
    revenue_today: str  # decimal string, all-inclusive
