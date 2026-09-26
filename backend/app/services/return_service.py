"""Returns. Wrong or counterfeit items are always returnable within the window (even when the
product is marked non-returnable), and an approved wrong/fake return lowers the seller's trust score
(see trust_service)."""

from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.errors import ConflictError, NotFoundError
from app.core.policies import RETURN_WINDOW_DAYS
from app.db.types import utcnow
from app.models.order import Order, OrderItem, OrderStatus
from app.models.returns import GUARANTEED_RETURN_REASONS, ReturnRequest, ReturnStatus
from app.models.seller import Seller
from app.services.trust_service import recompute_trust_score
from app.models.user import User
from app.schemas.returns import ReturnCreate, ReturnRead, ReturnResolve


def to_return_read(ret: ReturnRequest) -> ReturnRead:
    """``ret.order_item`` must be loaded."""
    return ReturnRead(
        id=ret.id,
        order_id=ret.order_item.order_id,
        order_item_id=ret.order_item_id,
        product_title=ret.order_item.title,
        reason=ret.reason,
        description=ret.description,
        status=ret.status,
        refund_amount=ret.refund_amount,
        resolution_note=ret.resolution_note,
        created_at=ret.created_at,
        resolved_at=ret.resolved_at,
    )


async def create_return(db: AsyncSession, user: User, data: ReturnCreate) -> ReturnRequest:
    stmt = (
        select(OrderItem)
        .join(Order, Order.id == OrderItem.order_id)
        .where(OrderItem.id == data.order_item_id, Order.user_id == user.id)
        .options(selectinload(OrderItem.order))
    )
    item = (await db.execute(stmt)).scalar_one_or_none()
    if item is None:
        raise NotFoundError(f"Order item {data.order_item_id} not found")

    order = item.order
    if order.status != OrderStatus.DELIVERED or order.delivered_at is None:
        raise ConflictError("A return can be requested once the order is delivered")
    deadline = order.delivered_at + timedelta(days=RETURN_WINDOW_DAYS)
    if utcnow() > deadline:
        raise ConflictError(f"The {RETURN_WINDOW_DAYS}-day return window closed on {deadline:%d %b %Y}")
    if data.reason not in GUARANTEED_RETURN_REASONS and not item.is_returnable:
        raise ConflictError("This item is non-returnable. Wrong or counterfeit items can still be returned.")

    existing = await db.execute(select(ReturnRequest.id).where(ReturnRequest.order_item_id == item.id))
    if existing.first() is not None:
        raise ConflictError("A return has already been requested for this item")

    ret = ReturnRequest(
        order_item_id=item.id,
        user_id=user.id,
        reason=data.reason,
        description=data.description.strip(),
        status=ReturnStatus.REQUESTED,
        refund_amount=item.line_total,
    )
    ret.order_item = item
    db.add(ret)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise ConflictError("A return has already been requested for this item") from exc
    return ret


_WITH_ITEM = selectinload(ReturnRequest.order_item)


async def list_customer_returns(db: AsyncSession, user: User) -> list[ReturnRequest]:
    stmt = select(ReturnRequest).where(ReturnRequest.user_id == user.id).options(_WITH_ITEM)
    return list((await db.execute(stmt.order_by(ReturnRequest.id.desc()))).scalars().all())


async def list_seller_returns(db: AsyncSession, seller: Seller) -> list[ReturnRequest]:
    stmt = (
        select(ReturnRequest)
        .join(OrderItem, OrderItem.id == ReturnRequest.order_item_id)
        .join(Order, Order.id == OrderItem.order_id)
        .where(Order.seller_id == seller.id)
        .options(_WITH_ITEM)
    )
    return list((await db.execute(stmt.order_by(ReturnRequest.id.desc()))).scalars().all())


async def list_all_returns(db: AsyncSession, status: ReturnStatus | None) -> list[ReturnRequest]:
    stmt = select(ReturnRequest).options(_WITH_ITEM)
    if status is not None:
        stmt = stmt.where(ReturnRequest.status == status)
    return list((await db.execute(stmt.order_by(ReturnRequest.id.desc()))).scalars().all())


async def resolve_return(db: AsyncSession, admin: User, return_id: int, data: ReturnResolve) -> ReturnRequest:
    stmt = (
        select(ReturnRequest)
        .where(ReturnRequest.id == return_id)
        .options(selectinload(ReturnRequest.order_item).selectinload(OrderItem.order))
        .with_for_update(of=ReturnRequest)
    )
    ret = (await db.execute(stmt)).scalar_one_or_none()
    if ret is None:
        raise NotFoundError(f"Return {return_id} not found")
    if ret.status != ReturnStatus.REQUESTED:
        raise ConflictError(f"This return was already {ret.status.value}")

    ret.status = ReturnStatus.APPROVED if data.decision == "approve" else ReturnStatus.REJECTED
    ret.resolution_note = data.note.strip()
    ret.resolved_by_id = admin.id
    ret.resolved_at = utcnow()
    if ret.status == ReturnStatus.APPROVED and ret.reason in GUARANTEED_RETURN_REASONS:
        await db.flush()  # so the recount below includes this approval
        await recompute_trust_score(db, ret.order_item.order.seller_id)
    await db.commit()
    return ret
