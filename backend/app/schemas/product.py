from datetime import datetime
from decimal import Decimal
from typing import Self

from pydantic import BaseModel, Field, HttpUrl, field_validator, model_validator

from app.schemas.pricing import PriceBreakdown
from app.schemas.review import RatingSummary
from app.schemas.seller import SellerCard
from app.services.size_service import validate_chart, validate_sizes

# A size-chart row: {"size": "M", "chest": 102, "length": 104} (garment measurements in cm).
SizeChartRow = dict[str, str | float]


class SizeStock(BaseModel):
    size: str = Field(min_length=1, max_length=20)
    stock: int = Field(default=0, ge=0)

    @field_validator("size")
    @classmethod
    def tidy_size(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Size can't be blank")
        return value


def _check_sizes(sizes: list[SizeStock] | None, chart: list[SizeChartRow] | None) -> None:
    names = [s.size for s in sizes or []]
    validate_sizes(names)
    if chart:
        if not names:
            raise ValueError("A size chart needs the product's sizes")
        validate_chart(chart, names)


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
    # Clothing etc.: per-size stock (``stock`` then becomes their sum) and an optional size chart.
    sizes: list[SizeStock] | None = Field(default=None, max_length=20)
    size_chart: list[SizeChartRow] | None = Field(default=None, max_length=20)

    @field_validator("category")
    @classmethod
    def normalise_category(cls, value: str) -> str:
        return value.strip().lower()

    @model_validator(mode="after")
    def check_sizes(self) -> Self:
        _check_sizes(self.sizes, self.size_chart)
        if self.sizes:
            self.stock = sum(s.stock for s in self.sizes)
        return self


class ProductUpdate(BaseModel):
    """Partial update by the owning seller. Omitted fields are unchanged."""

    title: str | None = Field(default=None, min_length=2, max_length=200)
    description: str | None = Field(default=None, min_length=1, max_length=5000)
    category: str | None = Field(default=None, min_length=2, max_length=100)
    base_price: Decimal | None = Field(default=None, gt=0, max_digits=10, decimal_places=2)
    delivery_fee: Decimal | None = Field(default=None, ge=0, max_digits=10, decimal_places=2)
    platform_fee: Decimal | None = Field(default=None, ge=0, max_digits=10, decimal_places=2)
    gst_percent: Decimal | None = Field(default=None, ge=0, le=100, max_digits=5, decimal_places=2)
    stock: int | None = Field(default=None, ge=0)
    is_returnable: bool | None = None
    country_of_origin: str | None = Field(default=None, min_length=2, max_length=100)
    image_url: HttpUrl | None = None
    # Sent = replaces the size list ([] removes sizes). A sized product's stock is their sum.
    sizes: list[SizeStock] | None = Field(default=None, max_length=20)
    # Sent = replaces the chart ([] removes it); checked against the product's sizes by the service.
    size_chart: list[SizeChartRow] | None = Field(default=None, max_length=20)

    @field_validator("category")
    @classmethod
    def normalise_category(cls, value: str | None) -> str | None:
        return value.strip().lower() if value else value

    @model_validator(mode="after")
    def check_sizes(self) -> Self:
        validate_sizes([s.size for s in self.sizes or []])
        return self


class FitRead(BaseModel):
    runs_small: int
    true_to_size: int
    runs_large: int
    verdict: str | None  # runs_small | true_to_size | runs_large | mixed; None = too few answers


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
    rating: RatingSummary
    sizes: list[SizeStock] = []  # empty for products without sizes
    size_chart: list[SizeChartRow] | None = None
    fit: FitRead | None = None  # what buyers said about the fit (sized products only)


class CategoryCount(BaseModel):
    category: str
    count: int


class ProductListResponse(BaseModel):
    items: list[ProductRead]
    total: int
    page: int
    page_size: int
