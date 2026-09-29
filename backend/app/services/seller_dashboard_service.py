"""Seller self-service: own products, product edits, dashboard numbers and recent reviews."""

from datetime import timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.errors import BadRequestError, NotFoundError
from app.db.types import utcnow
from app.models.order import Order, OrderItem, OrderStatus
from app.models.product import Product, ProductVariant
from app.models.returns import ReturnRequest, ReturnStatus
from app.models.review import Review, ReviewStatus
from app.models.seller import Seller
from app.schemas.product import ProductUpdate, SizeStock
from app.services.size_service import validate_chart
from app.services.embedding_service import embed_product

LOW_STOCK = 5
TEXT_FIELDS = {"title", "description", "category"}  # changing these changes the search embedding


async def list_products(db: AsyncSession, seller: Seller) -> list[Product]:
    stmt = (
        select(Product)
        .where(Product.seller_id == seller.id)
        .options(selectinload(Product.seller))
        .order_by(Product.stock.asc(), Product.id.desc())  # low stock first
    )
    return list((await db.execute(stmt)).scalars().all())


async def update_product(db: AsyncSession, seller: Seller, product_id: int, data: ProductUpdate) -> Product:
    stmt = (
        select(Product)
        .where(Product.id == product_id, Product.seller_id == seller.id)
        .options(selectinload(Product.seller))
        .with_for_update(of=Product)
    )
    product = (await db.execute(stmt)).scalar_one_or_none()
    if product is None:  # also when it's another seller's product: don't reveal it exists
        raise NotFoundError(f"Product {product_id} not found")
    # Only optional extras (photo, 3D model) can be cleared; null for a required field means "leave unchanged".
    clearable = {"image_url", "model_url", "model_credit", "try_on"}
    changes = {k: v for k, v in data.model_dump(exclude_unset=True).items() if v is not None or k in clearable}
    sizes, chart = changes.pop("sizes", None), changes.pop("size_chart", None)
    if sizes is not None:
        _replace_sizes(product, data.sizes or [])
    if chart is not None:
        product.size_chart = chart or None
    if product.size_chart:
        try:
            validate_chart(product.size_chart, [v.size for v in product.variants])
        except ValueError as exc:
            raise BadRequestError(str(exc)) from exc
    if product.has_sizes:
        changes.pop("stock", None)  # per-size stock wins; the total is derived below
        product.stock = sum(v.stock for v in product.variants)
    for key in ("image_url", "model_url"):
        if key in changes:
            changes[key] = str(changes[key]) if changes[key] else None
    for field, value in changes.items():
        setattr(product, field, value)
    if TEXT_FIELDS & changes.keys():
        await embed_product(product)
    await db.commit()
    return product


def _replace_sizes(product: Product, sizes: list[SizeStock]) -> None:
    """Make the product's sizes exactly ``sizes``, keeping existing rows (and their ids) where the
    size name is unchanged."""
    existing = {v.size: v for v in product.variants}
    variants = []
    for position, item in enumerate(sizes):
        variant = existing.get(item.size) or ProductVariant(size=item.size)
        variant.stock, variant.position = item.stock, position
        variants.append(variant)
    product.variants = variants  # removed sizes are deleted (delete-orphan)


async def dashboard(db: AsyncSession, seller: Seller) -> dict:
    now = utcnow()
    month_ago = now - timedelta(days=30)
    order_counts = dict(
        (await db.execute(select(Order.status, func.count(Order.id)).where(Order.seller_id == seller.id).group_by(Order.status))).all()
    )
    delivered_30d, revenue_30d = (
        await db.execute(
            select(
                func.count(Order.id).filter(Order.status == OrderStatus.DELIVERED, Order.delivered_at >= month_ago),
                func.coalesce(func.sum(Order.grand_total).filter(Order.status != OrderStatus.CANCELLED, Order.created_at >= month_ago), 0),
            ).where(Order.seller_id == seller.id)
        )
    ).one()
    open_returns = (
        await db.execute(
            select(func.count(ReturnRequest.id))
            .join(OrderItem, OrderItem.id == ReturnRequest.order_item_id)
            .join(Order, Order.id == OrderItem.order_id)
            .where(Order.seller_id == seller.id, ReturnRequest.status == ReturnStatus.REQUESTED)
        )
    ).scalar_one()
    products, low_stock = (
        await db.execute(
            select(func.count(Product.id), func.count(Product.id).filter(Product.stock <= LOW_STOCK)).where(
                Product.seller_id == seller.id
            )
        )
    ).one()
    avg_rating, review_count = (
        await db.execute(
            select(func.avg(Review.rating), func.count(Review.id))
            .join(Product, Product.id == Review.product_id)
            .where(Product.seller_id == seller.id, Review.status == ReviewStatus.PUBLISHED)
        )
    ).one()
    return {
        "to_ship": order_counts.get(OrderStatus.PLACED, 0),
        "in_transit": order_counts.get(OrderStatus.SHIPPED, 0),
        "delivered_30d": delivered_30d,
        "revenue_30d": str(Decimal(revenue_30d).quantize(Decimal("0.01"))),
        "open_returns": open_returns,
        "products": products,
        "low_stock": low_stock,
        "average_rating": round(float(avg_rating), 1) if avg_rating is not None else None,
        "review_count": review_count,
    }


async def recent_reviews(db: AsyncSession, seller: Seller, limit: int = 20) -> list[tuple[Review, str]]:
    stmt = (
        select(Review, Product.title)
        .join(Product, Product.id == Review.product_id)
        .where(Product.seller_id == seller.id, Review.status == ReviewStatus.PUBLISHED)
        .options(selectinload(Review.user))
        .order_by(Review.created_at.desc())
        .limit(limit)
    )
    return [(r, title) for r, title in (await db.execute(stmt)).all()]
