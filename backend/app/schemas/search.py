from decimal import Decimal
from typing import Literal

from pydantic import BaseModel

from app.schemas.product import ProductRead


class SearchUnderstanding(BaseModel):
    """What smart search read from the text, shown to the shopper so filtering is never hidden."""

    terms: list[str]
    categories: list[str]
    min_price: Decimal | None
    max_price: Decimal | None
    sort: Literal["relevance", "rating", "price_asc"]


class SearchResponse(BaseModel):
    query: str
    items: list[ProductRead]
    total: int
    understood: SearchUnderstanding | None = None
    # Nothing fitted the budget: the matching products with the nearest prices.
    closest: list[ProductRead] = []
