from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field, HttpUrl, field_validator

from app.schemas.pricing import PriceBreakdown
from app.schemas.seller import SellerCard


class ProductCreate(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    description: str = Field(min_length=1, max_length=5000)
    category: str = Field(min_length=2, max_length=100)
    base_price: Decimal = Field(gt=0, max_digits=10, decimal_places=2)
    delivery_fee: Decimal = Field(default=Decimal("0"), ge=0, max_digits=10, decimal_places=2)
    platform_fee: Decimal = Field(default=Decimal("0"), ge=0, max_digits=10, decimal_places=2)
    gst_percent: Decimal = Field(default=Decimal("18"), ge=0, le=100, max_digits=5, decimal_places=2)
    stock: int = Field(default=0, ge=0)
    is_returnable: bool = True
    country_of_origin: str = Field(default="India", min_length=2, max_length=100)
    image_url: HttpUrl | None = None

    @field_validator("category")
    @classmethod
    def normalise_category(cls, value: str) -> str:
        return value.strip().lower()


class ProductRead(BaseModel):
    id: int
    title: str
    description: str
    category: str
    stock: int
    is_returnable: bool
    country_of_origin: str
    image_url: str | None
    created_at: datetime
    price: PriceBreakdown
    seller: SellerCard


class CategoryCount(BaseModel):
    category: str
    count: int


class ProductListResponse(BaseModel):
    items: list[ProductRead]
    total: int
    page: int
    page_size: int
