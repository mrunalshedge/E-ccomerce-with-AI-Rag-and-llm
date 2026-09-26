"""Verified-purchase reviews with explainable fake-review detection.

Every honest review is published, good or bad. Reviews that look fake are *flagged*: kept out of
ratings, summaries and trust scores until an admin approves or removes them. Each flag records
machine-readable reasons, so moderators (and interviewers!) can see why.
"""

import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Literal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.ai.embeddings import embed_texts
from app.core.errors import ConflictError, NotFoundError, PermissionDeniedError
from app.core.policies import REVIEW_FLAG_THRESHOLD
from app.db.types import utcnow
from app.models.order import Order, OrderItem, OrderStatus
from app.models.product import Product
from app.models.review import Review, ReviewStatus
from app.models.user import User
from app.schemas.review import ReviewCreate, ReviewModerate, ReviewRead
from app.services.trust_service import recompute_trust_score

# ---------- fake-review signals ----------
# (code, weight). A review is flagged when the weights of the signals it trips reach 0.6.
DUPLICATE_TEXT = ("duplicate_text", 0.6)  # near-identical to another review (copy-paste farms)
CONTACT_OR_LINK = ("contact_or_link", 0.5)  # URLs, emails or phone numbers (spam/diversion)
RATING_BURST = ("rating_burst", 0.35)  # 3+ same-star reviews on one product within an hour
ONE_SELLER_FAN = ("one_seller_5_star_pattern", 0.35)  # reviewer only ever gives this seller 5★
SHORT_EXTREME = ("short_extreme_rating", 0.25)  # 1★/5★ with ≤ 4 words ("Best product!!")
TOO_FAST = ("reviewed_minutes_after_delivery", 0.15)  # before anyone could really use it

DUPLICATE_SIMILARITY = 0.92
BURST_WINDOW = timedelta(hours=1)
DUPLICATE_ORIGINAL_WINDOW = timedelta(days=7)
FAST_REVIEW_WINDOW = timedelta(minutes=10)
CONTACT_PATTERN = re.compile(r"(https?://|www\.|\b[\w.+-]+@[\w-]+\.\w+|(?:\+91[\s-]?)?\b[6-9]\d{9}\b)", re.I)


@dataclass(frozen=True)
class Assessment:
    score: float
    reasons: list[str]
    # The earlier review this one duplicates (if any), so it can be flagged too.
    duplicate_of: int | None = None


async def assess(
    db: AsyncSession,
    *,
    user: User,
    product: Product,
    rating: int,
    text: str,
    embedding: list[float] | None,
    delivered_at: datetime | None,
    now: datetime,
) -> Assessment:
    signals: list[tuple[str, float]] = []

    if CONTACT_PATTERN.search(text):
        signals.append(CONTACT_OR_LINK)
    # Count real words only: a URL or phone number padding a "Best!!" review shouldn't hide it.
    if rating in (1, 5) and len(re.findall(r"\w+", CONTACT_PATTERN.sub(" ", text))) <= 4:
        signals.append(SHORT_EXTREME)
    if delivered_at and now - delivered_at < FAST_REVIEW_WINDOW:
        signals.append(TOO_FAST)

    duplicate_of = None
    if embedding is not None:
        distance = Review.embedding.cosine_distance(embedding)
        closest = (
            await db.execute(
                select(Review.id, distance)
                .where(Review.embedding.is_not(None), Review.status != ReviewStatus.REMOVED)
                .order_by(distance)
                .limit(1)
            )
        ).first()
        if closest is not None and 1 - float(closest[1]) >= DUPLICATE_SIMILARITY:
            signals.append(DUPLICATE_TEXT)
            duplicate_of = closest[0]

    same_star_recently = await db.execute(
        select(func.count(Review.id)).where(
            Review.product_id == product.id,
            Review.rating == rating,
            Review.created_at >= now - BURST_WINDOW,
            Review.status != ReviewStatus.REMOVED,
        )
    )
    if same_star_recently.scalar_one() >= 2:  # this would be the 3rd within the hour
        signals.append(RATING_BURST)

    if rating == 5:
        history = (
            await db.execute(
                select(Review.rating, Product.seller_id)
                .join(Product, Product.id == Review.product_id)
                .where(Review.user_id == user.id)
            )
        ).all()
        if len(history) >= 2 and all(r == 5 and s == product.seller_id for r, s in history):
            signals.append(ONE_SELLER_FAN)

    return Assessment(
        score=round(min(1.0, sum(w for _, w in signals)), 2),
        reasons=[code for code, _ in signals],
        duplicate_of=duplicate_of,
    )


# ---------- create / read ----------


def reviewer_name(user: User) -> str:
    parts = user.name.split()
    return f"{parts[0]} {parts[-1][0]}." if len(parts) > 1 else parts[0]


def to_review_read(review: Review) -> ReviewRead:
    """``review.user`` must be loaded."""
    return ReviewRead(
        id=review.id,
        product_id=review.product_id,
        rating=review.rating,
        title=review.title,
        body=review.body,
        reviewer=reviewer_name(review.user),
        status=review.status,
        created_at=review.created_at,
    )


async def _reviewable_item(db: AsyncSession, user: User, product_id: int) -> OrderItem:
    """The customer's most recent delivered, not-yet-reviewed purchase of this product."""
    purchases = (
        await db.execute(
            select(OrderItem)
            .join(Order, Order.id == OrderItem.order_id)
            .where(Order.user_id == user.id, OrderItem.product_id == product_id)
            .options(selectinload(OrderItem.order))
            .order_by(OrderItem.id.desc())
        )
    ).scalars().all()
    if not purchases:
        raise PermissionDeniedError("Only customers who bought this product can review it")
    reviewed = set(
        (await db.execute(select(Review.order_item_id).where(Review.user_id == user.id))).scalars().all()
    )
    delivered = [p for p in purchases if p.order.status == OrderStatus.DELIVERED]
    open_items = [p for p in delivered if p.id not in reviewed]
    if open_items:
        return open_items[0]
    if delivered:
        raise ConflictError("You have already reviewed your purchase of this product")
    raise ConflictError("You can review this product once your order is delivered")


async def create_review(
    db: AsyncSession, user: User, product_id: int, data: ReviewCreate, *, now: datetime | None = None
) -> Review:
    """``now`` lets the demo seed back-date reviews; real requests use the current time."""
    now = now or utcnow()
    product = await db.get(Product, product_id)
    if product is None:
        raise NotFoundError(f"Product {product_id} not found")
    item = await _reviewable_item(db, user, product_id)

    text = f"{data.title or ''} {data.body}".strip()
    try:
        [embedding] = await embed_texts([text])
    except Exception:  # detection just skips the duplicate check
        embedding = None
    assessment = await assess(
        db,
        user=user,
        product=product,
        rating=data.rating,
        text=text,
        embedding=embedding,
        delivered_at=item.order.delivered_at,
        now=now,
    )
    review = Review(
        product_id=product_id,
        user_id=user.id,
        order_item_id=item.id,
        rating=data.rating,
        title=data.title,
        body=data.body.strip(),
        status=ReviewStatus.FLAGGED if assessment.score >= REVIEW_FLAG_THRESHOLD else ReviewStatus.PUBLISHED,
        suspicion_score=assessment.score,
        suspicion_reasons=assessment.reasons,
        embedding=embedding,
        created_at=now,
    )
    review.user = user
    db.add(review)
    if assessment.duplicate_of is not None:
        await _flag_original(db, assessment.duplicate_of, user_id=user.id, now=now)
    await db.flush()
    await recompute_trust_score(db, product.seller_id)
    await db.commit()
    return review


async def _flag_original(db: AsyncSession, review_id: int, *, user_id: int, now: datetime) -> None:
    """Copy-paste farms post one text from many accounts: when a recent review from *another*
    account is duplicated, the original is just as suspicious, so hold it for moderation too."""
    original = await db.get(Review, review_id)
    if (
        original is not None
        and original.user_id != user_id
        and original.status == ReviewStatus.PUBLISHED
        and now - original.created_at <= DUPLICATE_ORIGINAL_WINDOW
    ):
        original.status = ReviewStatus.FLAGGED
        original.suspicion_score = max(original.suspicion_score, DUPLICATE_TEXT[1])
        original.suspicion_reasons = [*original.suspicion_reasons, DUPLICATE_TEXT[0]]


SortOrder = Literal["recent", "highest", "lowest"]
_ORDER = {
    "recent": (Review.created_at.desc(), Review.id.desc()),
    "highest": (Review.rating.desc(), Review.created_at.desc()),
    "lowest": (Review.rating.asc(), Review.created_at.desc()),
}


async def list_published(
    db: AsyncSession, product_id: int, *, sort: SortOrder, page: int, page_size: int
) -> tuple[list[Review], int, int]:
    """(page of published reviews, total published, number under authenticity check)."""
    base = select(Review).where(Review.product_id == product_id, Review.status == ReviewStatus.PUBLISHED)
    total = (await db.execute(select(func.count()).select_from(base.subquery()))).scalar_one()
    under_review = (
        await db.execute(
            select(func.count(Review.id)).where(Review.product_id == product_id, Review.status == ReviewStatus.FLAGGED)
        )
    ).scalar_one()
    stmt = base.options(selectinload(Review.user)).order_by(*_ORDER[sort]).offset((page - 1) * page_size).limit(page_size)
    return list((await db.execute(stmt)).scalars().all()), total, under_review


async def list_my_reviews(db: AsyncSession, user: User) -> list[Review]:
    stmt = select(Review).where(Review.user_id == user.id).order_by(Review.id.desc())
    return list((await db.execute(stmt)).scalars().all())


# ---------- moderation ----------


async def list_for_moderation(db: AsyncSession, status: ReviewStatus | None) -> list[tuple[Review, str]]:
    stmt = select(Review, Product.title).join(Product, Product.id == Review.product_id).options(selectinload(Review.user))
    if status is not None:
        stmt = stmt.where(Review.status == status)
    stmt = stmt.order_by(Review.suspicion_score.desc(), Review.id.desc())
    return [(review, title) for review, title in (await db.execute(stmt)).all()]


async def moderate(db: AsyncSession, review_id: int, data: ReviewModerate) -> Review:
    stmt = select(Review).where(Review.id == review_id).options(selectinload(Review.user)).with_for_update(of=Review)
    review = (await db.execute(stmt)).scalar_one_or_none()
    if review is None:
        raise NotFoundError(f"Review {review_id} not found")
    if review.status == ReviewStatus.REMOVED:
        raise ConflictError("This review was already removed")
    if data.action == "approve" and review.status == ReviewStatus.PUBLISHED:
        raise ConflictError("This review is already published")

    review.status = ReviewStatus.PUBLISHED if data.action == "approve" else ReviewStatus.REMOVED
    review.moderation_note = data.note.strip()
    await db.flush()
    product = await db.get(Product, review.product_id)
    assert product is not None
    await recompute_trust_score(db, product.seller_id)
    await db.commit()
    return review
