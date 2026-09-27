import re
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

# 2-digit state code + PAN (5 letters, 4 digits, 1 letter) + entity no. + 'Z' + checksum.
GSTIN_PATTERN = r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]$"
PHONE_PATTERN = r"^\+?[0-9]{10,15}$"


class SellerCreate(BaseModel):
    business_name: str = Field(min_length=2, max_length=200)
    contact_email: EmailStr
    phone: str = Field(pattern=PHONE_PATTERN, examples=["+919876543210"])
    address: str = Field(min_length=10, max_length=500)
    gstin: str | None = Field(default=None, examples=["27ABCDE1234F1Z5"])
    grievance_officer_name: str = Field(min_length=2, max_length=120)
    grievance_officer_email: EmailStr

    @field_validator("gstin")
    @classmethod
    def validate_gstin(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip().upper()
        if not re.fullmatch(GSTIN_PATTERN, value):
            raise ValueError("Invalid GSTIN format")
        return value


class SellerCard(BaseModel):
    """Public seller details shown on every product listing."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    business_name: str
    contact_email: EmailStr
    phone: str
    address: str
    gstin: str | None
    grievance_officer_name: str
    grievance_officer_email: EmailStr
    trust_score: float


class SellerRead(SellerCard):
    user_id: int
    created_at: datetime


class TrustBreakdownRead(BaseModel):
    score: float
    wrong_or_fake_returns: int
    return_penalty: float
    average_rating: float | None
    review_count: int
    rating_penalty: float
    min_reviews_for_rating_penalty: int
    rating_target: float


class SellerDashboard(BaseModel):
    to_ship: int
    in_transit: int
    delivered_30d: int
    revenue_30d: str
    open_returns: int
    products: int
    low_stock: int
    average_rating: float | None
    review_count: int
    trust: TrustBreakdownRead


class SellerReviewRead(BaseModel):
    id: int
    product_id: int
    product_title: str
    rating: int
    title: str | None
    body: str
    reviewer: str
    created_at: datetime
