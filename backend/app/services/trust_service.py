"""Seller trust score (0–100), recomputed from the seller's full history so it's explainable:

    100 − 5 × (approved wrong-item / counterfeit returns)
        − 10 × (4.0 − average rating)   [only once the seller has ≥ 5 published reviews]
"""

from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.policies import (
    TRUST_MIN_REVIEWS,
    TRUST_PENALTY_WRONG_OR_FAKE,
    TRUST_RATING_TARGET,
    TRUST_RATING_WEIGHT,
)
from app.models.order import Order, OrderItem
from app.models.product import Product
from app.models.returns import GUARANTEED_RETURN_REASONS, ReturnRequest, ReturnStatus
from app.models.review import Review, ReviewStatus
from app.models.seller import Seller


@dataclass(frozen=True)
class TrustBreakdown:
    score: float
    wrong_or_fake_returns: int
    return_penalty: float
    average_rating: float | None
    review_count: int
    rating_penalty: float


async def trust_breakdown(db: AsyncSession, seller_id: int) -> TrustBreakdown:
    returns_stmt = (
        select(func.count(ReturnRequest.id))
        .join(OrderItem, OrderItem.id == ReturnRequest.order_item_id)
        .join(Order, Order.id == OrderItem.order_id)
        .where(
            Order.seller_id == seller_id,
            ReturnRequest.status == ReturnStatus.APPROVED,
            ReturnRequest.reason.in_(GUARANTEED_RETURN_REASONS),
        )
    )
    wrong_or_fake = (await db.execute(returns_stmt)).scalar_one()

    rating_stmt = (
        select(func.avg(Review.rating), func.count(Review.id))
        .join(Product, Product.id == Review.product_id)
        .where(Product.seller_id == seller_id, Review.status == ReviewStatus.PUBLISHED)
    )
    average, count = (await db.execute(rating_stmt)).one()
    average = float(average) if average is not None else None

    return_penalty = TRUST_PENALTY_WRONG_OR_FAKE * wrong_or_fake
    rating_penalty = 0.0
    if average is not None and count >= TRUST_MIN_REVIEWS and average < TRUST_RATING_TARGET:
        rating_penalty = round((TRUST_RATING_TARGET - average) * TRUST_RATING_WEIGHT, 1)
    score = max(0.0, min(100.0, 100.0 - return_penalty - rating_penalty))
    return TrustBreakdown(score, wrong_or_fake, return_penalty, average, count, rating_penalty)


async def recompute_trust_score(db: AsyncSession, seller_id: int) -> float:
    """Update the stored score (caller commits). Call after returns/reviews change."""
    breakdown = await trust_breakdown(db, seller_id)
    seller = (await db.execute(select(Seller).where(Seller.id == seller_id).with_for_update())).scalar_one()
    seller.trust_score = breakdown.score
    return breakdown.score
