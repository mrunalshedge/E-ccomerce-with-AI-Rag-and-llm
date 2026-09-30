from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.deps import DbSession
from app.core.rate_limit import rate_limit
from app.schemas.search import SearchResponse, SearchUnderstanding
from app.services import product_service, search_service

router = APIRouter(prefix="/search", tags=["search"])


@router.get("", response_model=SearchResponse, dependencies=[Depends(rate_limit("search", limit=60, window_seconds=60))])
async def search(
    db: DbSession,
    q: Annotated[str, Query(min_length=1, max_length=200, description="What you're looking for, in any language")],
    category: Annotated[str | None, Query(max_length=100)] = None,
    max_price: Annotated[Decimal | None, Query(gt=0, description="Max all-inclusive price (₹)")] = None,
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
    smart: Annotated[bool, Query(description="Read budgets, 'best'/'cheap' and category words from the text")] = True,
) -> SearchResponse:
    """Smart search: matches by meaning (English, हिंदी, मराठी) and by keywords, and understands
    budgets ("under 1000", "1000 से कम") and "best"/"cheapest"."""
    result = await search_service.search(db, q, category=category, max_price=max_price, smart=smart, limit=limit)
    items = await product_service.to_product_reads(db, [h.product for h in result.hits])
    closest = await product_service.to_product_reads(db, [h.product for h in result.closest])
    parsed = result.parsed
    understood = SearchUnderstanding(
        terms=parsed.terms,
        categories=sorted(parsed.categories),
        min_price=parsed.min_price,
        max_price=parsed.max_price,
        sort=parsed.sort,
    )
    return SearchResponse(query=q, items=items, total=len(items), understood=understood, closest=closest)
