"""Hybrid product search: meaning (pgvector cosine similarity) + keywords.

Semantic search finds "something cool to wear in summer" → cotton kurta, and works across
English/Hindi/Marathi. Keyword matching keeps exact names ("Kanjivaram") and brand-new products
without embeddings findable. Scores: cosine similarity, plus a boost for keyword hits.
"""

import logging
import re
from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.ai.embeddings import embed_texts
from app.models.product import Product
from app.services.product_service import price_of

logger = logging.getLogger(__name__)

# Below this cosine similarity a purely semantic match is treated as noise.
MIN_SIMILARITY = 0.30
# ...and semantic-only results scoring under half of the best hit are dropped (e.g. an exact
# keyword hit on "Kanjivaram" shouldn't be padded with loosely related items).
RELATIVE_CUTOFF = 0.5
KEYWORD_BOOST = 0.35
TITLE_BOOST = 0.15
CANDIDATES = 50


@dataclass
class SearchHit:
    product: Product
    score: float
    semantic: float
    keyword: bool


# Filler words that shouldn't count as keyword matches.
STOPWORDS = frozenset(
    "the and for with from under below above some something show want need give buy good best "
    "cheap price rupees please any all one".split()
)


def _keywords(query: str) -> list[str]:
    return list(dict.fromkeys(w for w in re.findall(r"\w+", query.lower()) if len(w) >= 3 and w not in STOPWORDS))


def _like(term: str) -> str:
    escaped = term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


async def search_products(
    db: AsyncSession,
    query: str,
    *,
    category: str | None = None,
    max_price: Decimal | None = None,
    in_stock_only: bool = False,
    limit: int = 20,
) -> list[SearchHit]:
    query = query.strip()
    if not query:
        return []

    filters = []
    if category:
        filters.append(Product.category == category.strip().lower())
    if in_stock_only:
        filters.append(Product.stock > 0)

    hits: dict[int, SearchHit] = {}

    # 1) Meaning: nearest neighbours by cosine distance (HNSW index). If the embedding model is
    #    unavailable (e.g. offline before its first download), degrade to keyword-only search.
    try:
        [query_vector] = await embed_texts([query])
    except Exception:
        logger.exception("Embedding failed; falling back to keyword search")
        query_vector = None
    if query_vector is not None:
        distance = Product.embedding.cosine_distance(query_vector)
        semantic_stmt = (
            select(Product, (1 - distance).label("similarity"))
            .where(Product.embedding.is_not(None), *filters)
            .options(selectinload(Product.seller))
            .order_by(distance)
            .limit(CANDIDATES)
        )
        for product, similarity in (await db.execute(semantic_stmt)).all():
            hits[product.id] = SearchHit(product, float(similarity), float(similarity), keyword=False)

    # 2) Keywords: individual words in the title/description ("Kanjivaram saree" must find
    #    "Kanjivaram Pure Silk Saree"). Scored by the share of query words that match.
    words = _keywords(query)
    if words:
        word_match = [
            or_(Product.title.ilike(_like(w), escape="\\"), Product.description.ilike(_like(w), escape="\\"))
            for w in words
        ]
        keyword_stmt = (
            select(Product).where(or_(*word_match), *filters).options(selectinload(Product.seller)).limit(CANDIDATES)
        )
        for product in (await db.execute(keyword_stmt)).scalars().all():
            title, text = product.title.lower(), f"{product.title} {product.description}".lower()
            share = sum(w in text for w in words) / len(words)
            title_share = sum(w in title for w in words) / len(words)
            hit = hits.get(product.id) or SearchHit(product, 0.0, 0.0, keyword=False)
            hit.keyword = share >= 0.5  # most of the query's words are there
            hit.score = hit.semantic + KEYWORD_BOOST * share + TITLE_BOOST * title_share
            hits[product.id] = hit

    best = max((h.score for h in hits.values()), default=0.0)
    cutoff = max(MIN_SIMILARITY, best * RELATIVE_CUTOFF)
    results = [h for h in hits.values() if h.keyword or h.semantic >= cutoff]
    if max_price is not None:
        results = [h for h in results if price_of(h.product).final_price <= max_price]
    results.sort(key=lambda h: h.score, reverse=True)
    return results[:limit]
