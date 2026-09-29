"""Checkout, order history, cancellation and seller fulfilment.

Anti-dark-pattern guarantees enforced here:
- the payment method is always the customer's explicit choice and never changed silently;
- checkout refuses to charge anything other than the total the customer saw (``expected_total``);
- product rows are locked during checkout so two buyers can't both get the last unit.
"""

from collections import defaultdict
from collections.abc import Sequence

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.errors import BadRequestError, ConflictError, NotFoundError
from app.db.types import utcnow
from app.models.cart import CartItem
from app.models.order import Order, OrderEvent, OrderItem, OrderStatus, PaymentMethod, PaymentStatus
from app.models.product import Product
from app.models.seller import Seller
from app.models.user import User, UserRole
from app.schemas.order import (
    CheckoutRequest,
    OrderEventRead,
    OrderItemRead,
    OrderRead,
    OrderStatusUpdate,
    SellerSummary,
)
from app.schemas.pricing import OrderTotals, PriceBreakdown
from app.services.pricing import line_total, summarise_lines
from app.services.cart_service import stock_of
from app.services.product_service import adjust_stock, price_of

ORDER_LOADERS = (selectinload(Order.items), selectinload(Order.events), selectinload(Order.seller))

# The only status changes a seller may make.
SELLER_TRANSITIONS: dict[OrderStatus, set[OrderStatus]] = {
    OrderStatus.PLACED: {OrderStatus.SHIPPED},
    OrderStatus.SHIPPED: {OrderStatus.DELIVERED},
}


# ---------- response building ----------


def _unit_price_of(item: OrderItem) -> PriceBreakdown:
    """Rebuild the breakdown from the snapshot taken at checkout (never recomputed)."""
    return PriceBreakdown(
        base_price=item.unit_base_price,
        delivery_fee=item.unit_delivery_fee,
        platform_fee=item.unit_platform_fee,
        taxable_value=item.unit_base_price + item.unit_delivery_fee + item.unit_platform_fee,
        gst_percent=item.gst_percent,
        gst_amount=item.unit_gst_amount,
        final_price=item.unit_final_price,
    )


def to_order_read(order: Order) -> OrderRead:
    """``order`` must be loaded with ``ORDER_LOADERS``."""
    return OrderRead(
        id=order.id,
        status=order.status,
        payment_method=order.payment_method,
        payment_status=order.payment_status,
        shipping_address=order.shipping_address,
        seller=SellerSummary.model_validate(order.seller),
        items=[
            OrderItemRead(
                id=item.id,
                product_id=item.product_id,
                title=item.title,
                size=item.size,
                quantity=item.quantity,
                unit_price=_unit_price_of(item),
                line_total=item.line_total,
                is_returnable=item.is_returnable,
            )
            for item in order.items
        ],
        totals=OrderTotals(
            items_count=sum(item.quantity for item in order.items),
            total_base=order.total_base,
            total_delivery=order.total_delivery,
            total_platform_fee=order.total_platform_fee,
            total_gst=order.total_gst,
            grand_total=order.grand_total,
        ),
        timeline=[OrderEventRead.model_validate(event) for event in order.events],
        created_at=order.created_at,
        delivered_at=order.delivered_at,
    )


async def _load_orders(db: AsyncSession, order_ids: Sequence[int]) -> list[Order]:
    stmt = (
        select(Order)
        .where(Order.id.in_(order_ids))
        .options(*ORDER_LOADERS)
        .order_by(Order.id)
        .execution_options(populate_existing=True)
    )
    return list((await db.execute(stmt)).scalars().all())


async def _lock_products(db: AsyncSession, product_ids: set[int]) -> dict[int, Product]:
    """SELECT ... FOR UPDATE, in id order so concurrent transactions can't deadlock.

    The product row lock also guards its sizes: every size-stock change locks the product first.
    ``populate_existing`` makes sure the sizes are re-read after the lock is taken."""
    stmt = (
        select(Product)
        .where(Product.id.in_(product_ids))
        .order_by(Product.id)
        .with_for_update(of=Product)
        .execution_options(populate_existing=True)
    )
    return {p.id: p for p in (await db.execute(stmt)).scalars().all()}


# ---------- customer ----------


async def checkout(db: AsyncSession, user: User, data: CheckoutRequest) -> list[Order]:
    """Turn the whole cart into orders (one per seller), atomically."""
    cart = (await db.execute(select(CartItem).where(CartItem.user_id == user.id).order_by(CartItem.id))).scalars().all()
    if not cart:
        raise BadRequestError("Your cart is empty")

    products = await _lock_products(db, {c.product_id for c in cart})
    priced: list[tuple[CartItem, Product, PriceBreakdown]] = []
    for cart_item in cart:
        product = products[cart_item.product_id]
        name = f"'{product.title}'" + (f" (size {cart_item.size})" if cart_item.size else "")
        if product.has_sizes != (cart_item.size is not None):
            raise ConflictError(f"The sizes of {name} have changed. Please update your cart.")
        stock = stock_of(product, cart_item.size)
        if cart_item.quantity > stock:
            left = f"only {stock} left" if stock else "out of stock"
            raise ConflictError(f"{name} is {left}. Please update your cart.")
        priced.append((cart_item, product, price_of(product)))

    totals = summarise_lines((unit, c.quantity) for c, _, unit in priced)
    if data.expected_total != totals.grand_total:
        raise ConflictError(
            f"The total is now ₹{totals.grand_total} (you saw ₹{data.expected_total}). "
            "Please review your cart before paying."
        )

    by_seller: dict[int, list[tuple[CartItem, Product, PriceBreakdown]]] = defaultdict(list)
    for line in priced:
        by_seller[line[1].seller_id].append(line)

    prepaid = data.payment_method != PaymentMethod.COD
    orders: list[Order] = []
    for seller_id, lines in sorted(by_seller.items()):
        seller_totals = summarise_lines((unit, c.quantity) for c, _, unit in lines)
        order = Order(
            user_id=user.id,
            seller_id=seller_id,
            status=OrderStatus.PLACED,
            payment_method=data.payment_method,
            payment_status=PaymentStatus.PAID if prepaid else PaymentStatus.PENDING,
            shipping_address=data.shipping_address.strip(),
            total_base=seller_totals.total_base,
            total_delivery=seller_totals.total_delivery,
            total_platform_fee=seller_totals.total_platform_fee,
            total_gst=seller_totals.total_gst,
            grand_total=seller_totals.grand_total,
        )
        order.items = [
            OrderItem(
                product_id=product.id,
                title=product.title,
                size=cart_item.size,
                quantity=cart_item.quantity,
                unit_base_price=unit.base_price,
                unit_delivery_fee=unit.delivery_fee,
                unit_platform_fee=unit.platform_fee,
                gst_percent=unit.gst_percent,
                unit_gst_amount=unit.gst_amount,
                unit_final_price=unit.final_price,
                line_total=line_total(unit, cart_item.quantity),
                is_returnable=product.is_returnable,
            )
            for cart_item, product, unit in lines
        ]
        note = (
            f"Order placed. Paid ₹{seller_totals.grand_total} by {data.payment_method.value.upper()} (simulated)."
            if prepaid
            else f"Order placed. Pay ₹{seller_totals.grand_total} in cash on delivery."
        )
        order.events = [OrderEvent(status=OrderStatus.PLACED, note=note, actor_user_id=user.id)]
        db.add(order)
        orders.append(order)
        for cart_item, product, _ in lines:
            adjust_stock(product, cart_item.size, -cart_item.quantity)

    await db.execute(delete(CartItem).where(CartItem.user_id == user.id))
    await db.commit()
    return await _load_orders(db, [o.id for o in orders])


async def list_customer_orders(db: AsyncSession, user: User) -> list[Order]:
    stmt = select(Order).where(Order.user_id == user.id).options(*ORDER_LOADERS).order_by(Order.id.desc())
    return list((await db.execute(stmt)).scalars().all())


async def get_order_for_user(db: AsyncSession, user: User, order_id: int) -> Order:
    """Customers see their own orders, sellers the orders they fulfil, admins everything.
    Anything else is reported as not found, so order ids can't be probed."""
    stmt = select(Order).where(Order.id == order_id).options(*ORDER_LOADERS)
    if user.role == UserRole.CUSTOMER:
        stmt = stmt.where(Order.user_id == user.id)
    elif user.role == UserRole.SELLER:
        stmt = stmt.join(Seller, Seller.id == Order.seller_id).where(Seller.user_id == user.id)
    order = (await db.execute(stmt)).scalar_one_or_none()
    if order is None:
        raise NotFoundError(f"Order {order_id} not found")
    return order


async def cancel_order(db: AsyncSession, user: User, order_id: int) -> Order:
    """Customer cancels before shipping: stock is restored and prepaid money refunded."""
    stmt = select(Order).where(Order.id == order_id, Order.user_id == user.id).with_for_update()
    order = (await db.execute(stmt)).scalar_one_or_none()
    if order is None:
        raise NotFoundError(f"Order {order_id} not found")
    if order.status == OrderStatus.CANCELLED:
        raise ConflictError("This order is already cancelled")
    if order.status != OrderStatus.PLACED:
        raise ConflictError("This order has already shipped. You can request a return after delivery.")

    items = (await db.execute(select(OrderItem).where(OrderItem.order_id == order.id))).scalars().all()
    products = await _lock_products(db, {i.product_id for i in items if i.product_id is not None})
    for item in items:
        if item.product_id in products:
            adjust_stock(products[item.product_id], item.size, item.quantity)

    refunded = order.payment_status == PaymentStatus.PAID
    order.status = OrderStatus.CANCELLED
    order.payment_status = PaymentStatus.REFUNDED if refunded else PaymentStatus.VOID
    note = f"Cancelled by customer. ₹{order.grand_total} refunded." if refunded else "Cancelled by customer."
    db.add(OrderEvent(order_id=order.id, status=OrderStatus.CANCELLED, note=note, actor_user_id=user.id))
    await db.commit()
    return (await _load_orders(db, [order.id]))[0]


# ---------- seller ----------


async def list_seller_orders(db: AsyncSession, seller: Seller) -> list[Order]:
    stmt = select(Order).where(Order.seller_id == seller.id).options(*ORDER_LOADERS).order_by(Order.id.desc())
    return list((await db.execute(stmt)).scalars().all())


async def update_status_by_seller(
    db: AsyncSession, seller: Seller, actor: User, order_id: int, data: OrderStatusUpdate
) -> Order:
    stmt = select(Order).where(Order.id == order_id, Order.seller_id == seller.id).with_for_update()
    order = (await db.execute(stmt)).scalar_one_or_none()
    if order is None:
        raise NotFoundError(f"Order {order_id} not found")
    if data.status not in SELLER_TRANSITIONS.get(order.status, set()):
        raise ConflictError(f"Cannot change an order from '{order.status.value}' to '{data.status.value}'")

    order.status = data.status
    default_note = "Shipped by seller."
    if data.status == OrderStatus.DELIVERED:
        order.delivered_at = utcnow()
        default_note = "Delivered."
        if order.payment_method == PaymentMethod.COD:
            order.payment_status = PaymentStatus.PAID
            default_note = f"Delivered. ₹{order.grand_total} collected in cash."
    db.add(
        OrderEvent(order_id=order.id, status=data.status, note=data.note or default_note, actor_user_id=actor.id)
    )
    await db.commit()
    return (await _load_orders(db, [order.id]))[0]
