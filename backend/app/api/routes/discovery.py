from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel

from app.api.deps import CurrentUser, DbSession, OptionalUser
from app.core.errors import NotFoundError
from app.core.rate_limit import rate_limit
from app.models.product import Product
from app.schemas.product import ProductRead
from app.services import discovery_service, product_service

router = APIRouter(tags=["discovery"])


class SuggestionRead(BaseModel):
    text: str
    kind: Literal["product", "category", "seller"]
    product_id: int | None = None
    category: str | None = None


class RecommendationRead(BaseModel):
    product: ProductRead
    reason: Literal["bought_together", "similar_interest", "popular"]


@router.get(
    "/search/suggest",
    response_model=list[SuggestionRead],
    dependencies=[Depends(rate_limit("suggest", limit=120, window_seconds=60))],
)
async def suggest(
    db: DbSession,
    q: Annotated[str, Query(max_length=100)],
    limit: Annotated[int, Query(ge=1, le=10)] = 8,
) -> list[SuggestionRead]:
    """Autocomplete from a prefix trie: products (matching any word of the title), categories
    and sellers, ranked by popularity and ratings. O(prefix length) per keystroke."""
    return [
        SuggestionRead(
            text=s.text,
            kind=s.kind,  # type: ignore[arg-type]
            product_id=s.ref if s.kind == "product" else None,  # type: ignore[arg-type]
            category=s.ref if s.kind == "category" else None,  # type: ignore[arg-type]
        )
        for s in await discovery_service.suggest(db, q, limit)
    ]


@router.get("/products/{product_id}/bought-together", response_model=list[ProductRead])
async def bought_together(
    product_id: int, db: DbSession, limit: Annotated[int, Query(ge=1, le=12)] = 4
) -> list[ProductRead]:
    """Products customers bought together with this one (co-purchase graph, with a 2-hop
    fallback), in stock only."""
    if await db.get(Product, product_id) is None:
        raise NotFoundError(f"Product {product_id} not found")
    products = await discovery_service.bought_together(db, product_id, limit)
    return await product_service.to_product_reads(db, products)


@router.get("/recommendations", response_model=list[RecommendationRead])
async def recommendations(
    db: DbSession,
    user: OptionalUser,
    seen: Annotated[str | None, Query(max_length=200, description="Comma-separated product ids a guest viewed")] = None,
    limit: Annotated[int, Query(ge=1, le=24)] = 8,
) -> list[RecommendationRead]:
    """Personalised top-K picks (heap selection over scored candidates), each with a reason."""
    seen_ids = [int(x) for x in (seen or "").split(",") if x.strip().isdigit()][:12]
    recs = await discovery_service.recommend(db, user, seen_ids, limit)
    reads = await product_service.to_product_reads(db, [r.product for r in recs])
    return [RecommendationRead(product=p, reason=r.reason) for p, r in zip(reads, recs, strict=True)]  # type: ignore[arg-type]


@router.post("/me/recently-viewed/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def record_view(product_id: int, user: CurrentUser, db: DbSession) -> None:
    """Remember that you viewed a product (per-user LRU, last 12)."""
    if await db.get(Product, product_id) is None:
        raise NotFoundError(f"Product {product_id} not found")
    discovery_service.recently_viewed.record(user.id, product_id)


@router.get("/me/recently-viewed", response_model=list[ProductRead])
async def list_recently_viewed(user: CurrentUser, db: DbSession) -> list[ProductRead]:
    """Most recent first."""
    return await product_service.to_product_reads(db, await discovery_service.recently_viewed_products(db, user))
