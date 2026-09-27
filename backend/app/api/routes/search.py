from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.deps import DbSession
from app.core.rate_limit import rate_limit
from app.schemas.search import SearchResponse
from app.services import product_service, search_service

router = APIRouter(prefix="/search", tags=["search"])


@router.get("", response_model=SearchResponse, dependencies=[Depends(rate_limit("search", limit=60, window_seconds=60))])
async def search(
    db: DbSession,
    q: Annotated[str, Query(min_length=1, max_length=200, description="What you're looking for, in any language")],
    category: Annotated[str | None, Query(max_length=100)] = None,
    max_price: Annotated[Decimal | None, Query(gt=0, description="Max all-inclusive price (₹)")] = None,
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
) -> SearchResponse:
    """Smart search: matches by meaning (English, हिंदी, मराठी) and by keywords."""
    hits = await search_service.search_products(db, q, category=category, max_price=max_price, limit=limit)
    items = await product_service.to_product_reads(db, [h.product for h in hits])
    return SearchResponse(query=q, items=items, total=len(hits))
