"""Rating aggregates over published (i.e. honest, verified) reviews only."""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.review import Review, ReviewStatus
from app.schemas.review import RatingSummary


async def rating_summaries(db: AsyncSession, product_ids: list[int]) -> dict[int, RatingSummary]:
    """Average rating and count per product (products without reviews get count 0)."""
    result = {pid: RatingSummary(average=None, count=0) for pid in product_ids}
    if not product_ids:
        return result
    stmt = (
        select(Review.product_id, func.avg(Review.rating), func.count(Review.id))
        .where(Review.product_id.in_(product_ids), Review.status == ReviewStatus.PUBLISHED)
        .group_by(Review.product_id)
    )
    for product_id, average, count in (await db.execute(stmt)).all():
        result[product_id] = RatingSummary(average=round(float(average), 1), count=count)
    return result


async def rating_distribution(db: AsyncSession, product_id: int) -> dict[str, int]:
    """How many published reviews gave 1..5 stars."""
    distribution = {str(stars): 0 for stars in range(1, 6)}
    stmt = (
        select(Review.rating, func.count(Review.id))
        .where(Review.product_id == product_id, Review.status == ReviewStatus.PUBLISHED)
        .group_by(Review.rating)
    )
    for rating, count in (await db.execute(stmt)).all():
        distribution[str(rating)] = count
    return distribution


async def fit_counts(db: AsyncSession, product_ids: list[int]) -> dict[int, dict[str, int]]:
    """How many published reviews said runs small / true to size / runs large, per product."""
    result: dict[int, dict[str, int]] = {pid: {} for pid in product_ids}
    if not product_ids:
        return result
    stmt = (
        select(Review.product_id, Review.fit, func.count(Review.id))
        .where(Review.product_id.in_(product_ids), Review.status == ReviewStatus.PUBLISHED, Review.fit.is_not(None))
        .group_by(Review.product_id, Review.fit)
    )
    for product_id, fit, count in (await db.execute(stmt)).all():
        result[product_id][fit.value] = count
    return result
