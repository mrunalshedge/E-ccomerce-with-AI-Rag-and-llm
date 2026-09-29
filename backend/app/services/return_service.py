"""Returns. Wrong or counterfeit items are always returnable within the window (even when the
product is marked non-returnable), and an approved wrong/fake return lowers the seller's trust score
(see trust_service).

Wrong size: the customer can ask for a refund or an exchange to another size. An approved exchange
refunds nothing, puts the returned (unused) size back in stock and reserves the new one; if the new
size has sold out by then, the exchange becomes a full refund instead of leaving the customer stuck."""

from datetime import timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.errors import BadRequestError, ConflictError, NotFoundError
from app.core.policies import RETURN_WINDOW_DAYS
from app.db.types import utcnow
from app.models.order import Order, OrderItem, OrderStatus
from app.models.product import Product
from app.models.returns import GUARANTEED_RETURN_REASONS, ReturnReason, ReturnRequest, ReturnStatus
from app.models.seller import Seller
from app.services.cart_service import stock_of
from app.services.product_service import adjust_stock
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
        size=ret.order_item.size,
        reason=ret.reason,
        exchange_size=ret.exchange_size,
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

    exchange_size = data.exchange_size.strip() if data.exchange_size else None
    if data.reason == ReturnReason.WRONG_SIZE and item.size is None:
        raise BadRequestError("This item wasn't bought in a size; choose another reason")
    if exchange_size is not None:
        await _check_exchange(db, item, data.reason, exchange_size)

    existing = await db.execute(select(ReturnRequest.id).where(ReturnRequest.order_item_id == item.id))
    if existing.first() is not None:
        raise ConflictError("A return has already been requested for this item")

    ret = ReturnRequest(
        order_item_id=item.id,
        user_id=user.id,
        reason=data.reason,
        description=data.description.strip(),
        status=ReturnStatus.REQUESTED,
        refund_amount=Decimal("0.00") if exchange_size else item.line_total,
        exchange_size=exchange_size,
    )
    ret.order_item = item
    db.add(ret)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise ConflictError("A return has already been requested for this item") from exc
    return ret


async def _check_exchange(db: AsyncSession, item: OrderItem, reason: ReturnReason, size: str) -> None:
    if reason != ReturnReason.WRONG_SIZE:
        raise BadRequestError("An exchange to another size is only for the 'wrong size' reason")
    if size == item.size:
        raise BadRequestError("Choose a different size from the one you received")
    product = await db.get(Product, item.product_id) if item.product_id else None
    if product is None or product.variant(size) is None:
        raise BadRequestError(f"Size {size} isn't available for this product")
    if stock_of(product, size) < item.quantity:
        raise ConflictError(f"Size {size} is out of stock right now; you can ask for a refund instead")


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
    if ret.status == ReturnStatus.APPROVED and ret.reason == ReturnReason.WRONG_SIZE:
        await _settle_wrong_size(db, ret)
    if ret.status == ReturnStatus.APPROVED and ret.reason in GUARANTEED_RETURN_REASONS:
        await db.flush()  # so the recount below includes this approval
        await recompute_trust_score(db, ret.order_item.order.seller_id)
    await db.commit()
    return ret


async def _settle_wrong_size(db: AsyncSession, ret: ReturnRequest) -> None:
    """Approved wrong-size return: restock the returned size and, for an exchange, reserve the new
    one (or fall back to a full refund if it sold out meanwhile)."""
    item = ret.order_item
    product = None
    if item.product_id is not None:
        stmt = (
            select(Product)
            .where(Product.id == item.product_id)
            .with_for_update(of=Product)
            .execution_options(populate_existing=True)
        )
        product = (await db.execute(stmt)).scalar_one_or_none()
    if product is not None:
        adjust_stock(product, item.size, item.quantity)
    if ret.exchange_size is None:
        return
    if product is not None and stock_of(product, ret.exchange_size) >= item.quantity:
        adjust_stock(product, ret.exchange_size, -item.quantity)
        ret.resolution_note = f"{ret.resolution_note} Exchange: size {ret.exchange_size} will be sent."[:500]
    else:
        ret.refund_amount = item.line_total
        ret.resolution_note = (
            f"{ret.resolution_note} Size {ret.exchange_size} sold out, so ₹{item.line_total} is refunded instead."
        )[:500]
