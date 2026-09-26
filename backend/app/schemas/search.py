from pydantic import BaseModel

from app.schemas.product import ProductRead


class SearchResponse(BaseModel):
    query: str
    items: list[ProductRead]
    total: int
