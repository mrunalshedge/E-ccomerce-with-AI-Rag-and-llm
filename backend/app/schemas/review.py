from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.models.review import ReviewFit, ReviewStatus


class RatingSummary(BaseModel):
    average: float | None  # None until the first published review
    count: int


class ReviewCreate(BaseModel):
    rating: int = Field(ge=1, le=5)
    fit: ReviewFit | None = None  # "How does it fit?" — only for products that come in sizes
    title: str | None = Field(default=None, max_length=120)
    body: str = Field(min_length=10, max_length=2000)

    @field_validator("title")
    @classmethod
    def blank_title_is_none(cls, value: str | None) -> str | None:
        return value.strip() or None if value else None


class ReviewRead(BaseModel):
    id: int
    product_id: int
    rating: int
    fit: ReviewFit | None = None
    title: str | None
    body: str
    reviewer: str  # "Asha K." — first name + initial, never the full name or email
    verified_purchase: bool = True
    status: ReviewStatus
    created_at: datetime


class ReviewStats(RatingSummary):
    distribution: dict[str, int]  # "1".."5" → count
    under_review: int  # flagged as possibly fake, excluded from the stats until checked


class ReviewListResponse(BaseModel):
    items: list[ReviewRead]
    total: int
    page: int
    page_size: int
    stats: ReviewStats


class MyReview(BaseModel):
    id: int
    product_id: int
    order_item_id: int
    rating: int
    status: ReviewStatus


class ReviewSummaryResponse(BaseModel):
    status: Literal["ready", "not_enough_reviews", "unavailable"]
    summary: str | None
    review_count: int
    generated_at: datetime | None


class AdminReviewRead(ReviewRead):
    suspicion_score: float
    suspicion_reasons: list[str]
    moderation_note: str | None
    product_title: str


class ReviewModerate(BaseModel):
    action: Literal["approve", "remove"]
    note: str = Field(min_length=3, max_length=500)
