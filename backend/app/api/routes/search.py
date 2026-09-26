from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Query

from app.api.deps import DbSession
from app.schemas.search import SearchResponse
from app.services import search_service
from app.services.product_service import to_product_read

router = APIRouter(prefix="/search", tags=["search"])


@router.get("", response_model=SearchResponse)
async def search(
    db: DbSession,
    q: Annotated[str, Query(min_length=1, max_length=200, description="What you're looking for, in any language")],
    category: Annotated[str | None, Query(max_length=100)] = None,
    max_price: Annotated[Decimal | None, Query(gt=0, description="Max all-inclusive price (₹)")] = None,
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
) -> SearchResponse:
    """Smart search: matches by meaning (English, हिंदी, मराठी) and by keywords."""
    hits = await search_service.search_products(db, q, category=category, max_price=max_price, limit=limit)
    return SearchResponse(query=q, items=[to_product_read(h.product) for h in hits], total=len(hits))
