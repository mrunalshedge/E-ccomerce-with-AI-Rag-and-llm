"""Customer cart. Items are only added by the customer's own request; prices are always the
live all-inclusive product prices."""

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.errors import BadRequestError, ConflictError, NotFoundError
from app.core.policies import MAX_QUANTITY_PER_ITEM
from app.models.cart import CartItem
from app.models.product import Product
from app.models.user import User
from app.schemas.cart import CartItemAdd, CartLine, CartRead
from app.services.pricing import line_total, summarise_lines
from app.services.product_service import price_of


def check_quantity_available(product: Product, quantity: int) -> None:
    """Raise if ``quantity`` of ``product`` can't be bought right now."""
    if quantity > MAX_QUANTITY_PER_ITEM:
        raise BadRequestError(f"You can buy at most {MAX_QUANTITY_PER_ITEM} of one item")
    if product.stock == 0:
        raise ConflictError(f"'{product.title}' is out of stock")
    if quantity > product.stock:
        raise ConflictError(f"Only {product.stock} of '{product.title}' left in stock")


async def get_cart(db: AsyncSession, user: User) -> CartRead:
    stmt = (
        select(CartItem)
        .where(CartItem.user_id == user.id)
        .options(selectinload(CartItem.product).selectinload(Product.seller))
        .order_by(CartItem.id)
    )
    items = (await db.execute(stmt)).scalars().all()

    lines: list[CartLine] = []
    for item in items:
        unit = price_of(item.product)
        lines.append(
            CartLine(
                product_id=item.product_id,
                title=item.product.title,
                category=item.product.category,
                image_url=item.product.image_url,
                seller_id=item.product.seller_id,
                seller_name=item.product.seller.business_name,
                quantity=item.quantity,
                available_stock=item.product.stock,
                unit_price=unit,
                line_total=line_total(unit, item.quantity),
            )
        )
    totals = summarise_lines((line.unit_price, line.quantity) for line in lines)
    return CartRead(items=lines, totals=totals)


async def _find_item(db: AsyncSession, user: User, product_id: int) -> CartItem | None:
    stmt = select(CartItem).where(CartItem.user_id == user.id, CartItem.product_id == product_id)
    return (await db.execute(stmt)).scalar_one_or_none()


async def add_item(db: AsyncSession, user: User, data: CartItemAdd) -> CartRead:
    """Add a product, or increase its quantity if it's already in the cart."""
    product = await db.get(Product, data.product_id)
    if product is None:
        raise NotFoundError(f"Product {data.product_id} not found")

    existing = await _find_item(db, user, data.product_id)
    new_quantity = (existing.quantity if existing else 0) + data.quantity
    check_quantity_available(product, new_quantity)

    if existing:
        existing.quantity = new_quantity
    else:
        db.add(CartItem(user_id=user.id, product_id=product.id, quantity=new_quantity))
    try:
        await db.commit()
    except IntegrityError as exc:  # the same product added twice concurrently
        await db.rollback()
        raise ConflictError("This product was just added to your cart; please retry") from exc
    return await get_cart(db, user)


async def update_quantity(db: AsyncSession, user: User, product_id: int, quantity: int) -> CartRead:
    item = await _find_item(db, user, product_id)
    if item is None:
        raise NotFoundError("This product is not in your cart")
    product = await db.get(Product, product_id)
    assert product is not None  # cart rows are deleted with their product
    check_quantity_available(product, quantity)
    item.quantity = quantity
    await db.commit()
    return await get_cart(db, user)


async def remove_item(db: AsyncSession, user: User, product_id: int) -> CartRead:
    item = await _find_item(db, user, product_id)
    if item is None:
        raise NotFoundError("This product is not in your cart")
    await db.delete(item)
    await db.commit()
    return await get_cart(db, user)
