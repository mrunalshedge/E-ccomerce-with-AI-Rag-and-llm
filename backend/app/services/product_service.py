from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.errors import NotFoundError
from app.models.product import Product
from app.models.seller import Seller
from app.schemas.pricing import PriceBreakdown
from app.schemas.product import ProductCreate, ProductRead
from app.schemas.seller import SellerCard
from app.services.pricing import calculate_price_breakdown


def price_of(product: Product) -> PriceBreakdown:
    """Current all-inclusive unit price of a product."""
    return calculate_price_breakdown(
        base_price=product.base_price,
        delivery_fee=product.delivery_fee,
        platform_fee=product.platform_fee,
        gst_percent=product.gst_percent,
    )


def to_product_read(product: Product) -> ProductRead:
    """Build the public product response: product fields + price breakdown + seller card.
    ``product.seller`` must already be loaded."""
    return ProductRead(
        id=product.id,
        title=product.title,
        description=product.description,
        category=product.category,
        stock=product.stock,
        is_returnable=product.is_returnable,
        country_of_origin=product.country_of_origin,
        image_url=product.image_url,
        created_at=product.created_at,
        price=price_of(product),
        seller=SellerCard.model_validate(product.seller),
    )


async def list_products(
    db: AsyncSession, *, category: str | None, q: str | None = None, page: int, page_size: int
) -> tuple[list[Product], int]:
    """Return one page of products (newest first) and the total count.

    ``q`` is a simple keyword filter on title/description; meaning-based search comes in Phase 3.
    """
    conditions = []
    if category:
        conditions.append(Product.category == category.strip().lower())
    if q and q.strip():
        # Escape LIKE wildcards so "50%" or "t_shirt" match literally.
        term = q.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        pattern = f"%{term}%"
        conditions.append(
            or_(Product.title.ilike(pattern, escape="\\"), Product.description.ilike(pattern, escape="\\"))
        )

    stmt = select(Product).options(selectinload(Product.seller)).where(*conditions)
    count_stmt = select(func.count()).select_from(Product).where(*conditions)

    stmt = stmt.order_by(Product.created_at.desc(), Product.id.desc())
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)

    total = (await db.execute(count_stmt)).scalar_one()
    products = list((await db.execute(stmt)).scalars().all())
    return products, total


async def get_product(db: AsyncSession, product_id: int) -> Product:
    stmt = select(Product).options(selectinload(Product.seller)).where(Product.id == product_id)
    product = (await db.execute(stmt)).scalar_one_or_none()
    if product is None:
        raise NotFoundError(f"Product {product_id} not found")
    return product


async def create_product(db: AsyncSession, seller: Seller, data: ProductCreate) -> Product:
    values = data.model_dump()
    values["image_url"] = str(data.image_url) if data.image_url else None
    product = Product(seller_id=seller.id, **values)
    product.seller = seller  # already loaded; lets the response build without another query
    db.add(product)
    await db.commit()
    return product


async def list_categories(db: AsyncSession) -> list[tuple[str, int]]:
    """Categories that have products, with counts (most products first)."""
    stmt = (
        select(Product.category, func.count())
        .group_by(Product.category)
        .order_by(func.count().desc(), Product.category)
    )
    return [(category, count) for category, count in (await db.execute(stmt)).all()]
