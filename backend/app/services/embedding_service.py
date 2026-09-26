"""Keeps product embeddings (pgvector) in sync with product text."""

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.embeddings import embed_texts, product_text
from app.models.product import Product

logger = logging.getLogger(__name__)

BATCH_SIZE = 32


async def embed_product(product: Product) -> bool:
    """Set ``product.embedding`` (caller commits). Never raises: a missing embedding only means the
    product is found by keyword instead of meaning until ``npm run embed`` fills it in."""
    try:
        [vector] = await embed_texts([product_text(product)])
    except Exception:  # model download/load failure must not block listing a product
        logger.exception("Could not embed product %s", product.id)
        return False
    product.embedding = vector
    return True


async def backfill_embeddings(db: AsyncSession, *, recompute: bool = False) -> int:
    """Embed products that have no embedding (or all products with ``recompute``). Returns count."""
    stmt = select(Product).order_by(Product.id)
    if not recompute:
        stmt = stmt.where(Product.embedding.is_(None))
    products = list((await db.execute(stmt)).scalars().all())

    for start in range(0, len(products), BATCH_SIZE):
        batch = products[start : start + BATCH_SIZE]
        vectors = await embed_texts([product_text(p) for p in batch])
        for product, vector in zip(batch, vectors, strict=True):
            product.embedding = vector
        await db.commit()
    return len(products)
