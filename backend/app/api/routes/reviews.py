from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.ai.llm import AssistantModels, get_assistant_models
from app.api.deps import CustomerUser, DbSession
from app.core.rate_limit import rate_limit
from app.schemas.review import (
    MyReview,
    ReviewCreate,
    ReviewListResponse,
    ReviewRead,
    ReviewStats,
    ReviewSummaryResponse,
)
from app.services import review_service, summary_service
from app.services.rating_service import rating_distribution, rating_summaries
from app.services.review_service import SortOrder, to_review_read

router = APIRouter(tags=["reviews"])


@router.get("/products/{product_id}/reviews", response_model=ReviewListResponse)
async def list_reviews(
    product_id: int,
    db: DbSession,
    sort: SortOrder = "recent",
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=50)] = 10,
) -> ReviewListResponse:
    """All published reviews, good and bad; every one is from a verified purchase.
    Reviews flagged as possibly fake are excluded and only counted in `stats.under_review`."""
    reviews, total, under_review = await review_service.list_published(
        db, product_id, sort=sort, page=page, page_size=page_size
    )
    summary = (await rating_summaries(db, [product_id]))[product_id]
    return ReviewListResponse(
        items=[to_review_read(r) for r in reviews],
        total=total,
        page=page,
        page_size=page_size,
        stats=ReviewStats(
            average=summary.average,
            count=summary.count,
            distribution=await rating_distribution(db, product_id),
            under_review=under_review,
        ),
    )


@router.post(
    "/products/{product_id}/reviews",
    response_model=ReviewRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit("review", limit=10, window_seconds=3600, per="user"))],
)
async def create_review(product_id: int, data: ReviewCreate, user: CustomerUser, db: DbSession) -> ReviewRead:
    """Review a product you bought and received. `status` is `flagged` if it looks fake
    (an admin checks it before it counts)."""
    return to_review_read(await review_service.create_review(db, user, product_id, data))


@router.get(
    "/products/{product_id}/reviews/summary",
    response_model=ReviewSummaryResponse,
    dependencies=[Depends(rate_limit("summary", limit=30, window_seconds=60))],  # may call Gemini
)
async def review_summary(
    product_id: int,
    db: DbSession,
    models: Annotated[AssistantModels | None, Depends(get_assistant_models)],
    language: Annotated[str, Query(pattern="^(en|hi|mr)$")] = "en",
) -> ReviewSummaryResponse:
    """AI summary (pros/cons) of the published verified reviews, cached per language."""
    result = await summary_service.get_summary(db, models, product_id, language)
    return ReviewSummaryResponse(
        status=result.status,  # type: ignore[arg-type]
        summary=result.summary,
        review_count=result.review_count,
        generated_at=result.generated_at,
    )


@router.get("/reviews/mine", response_model=list[MyReview])
async def my_reviews(user: CustomerUser, db: DbSession) -> list[MyReview]:
    """Your reviews, so the app can show which purchases you've already reviewed."""
    return [
        MyReview(id=r.id, product_id=r.product_id, order_item_id=r.order_item_id, rating=r.rating, status=r.status)
        for r in await review_service.list_my_reviews(db, user)
    ]
