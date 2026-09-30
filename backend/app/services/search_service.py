"""Hybrid product search: keywords + meaning (pgvector cosine similarity), with query understanding.

1. ``query_parser`` turns "which is best kurta under 1000" into terms ["kurta", "kurti"], a ₹1000
   budget and "best rated first", translating Hindi/Marathi/Hinglish product words on the way.
2. Candidates come from whole-word keyword matches (title, description, category) and from the
   nearest neighbours of the query embedding (HNSW index).
3. Results are ranked in tiers, so exact matches always beat "sort of related":
   title match > right category > description match > strong meaning-only match.
   Weak meaning-only matches are dropped instead of padding the list (rice for "kurta").
4. The budget is applied last; if nothing fits, the closest-priced matches are returned separately
   so the shopper sees why the list is empty instead of a silent "no results".
"""

import logging
import re
from dataclasses import dataclass, field
from decimal import Decimal

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.ai.embeddings import embed_texts
from app.models.product import Product
from app.services.product_service import price_of
from app.services.query_parser import ParsedQuery, parse_query
from app.services.rating_service import rating_summaries

logger = logging.getLogger(__name__)

CANDIDATES = 60
# Meaning-only matches must be close in absolute terms AND close to the best meaning match.
MIN_SIMILARITY = 0.42
RELATIVE_CUTOFF = 0.8
# ...and stricter still when real keyword/category matches exist, so they aren't diluted.
MIN_SIMILARITY_WITH_MATCHES = 0.5
# A description-only match on some of the words needs at least this much meaning-match too
# ("cool" in "keep rooms cool" is not "something cool for summer").
PARTIAL_DESCRIPTION_MIN_SIMILARITY = 0.3
# Bayesian prior for "best rated": pulls products with few reviews towards 3.5★.
PRIOR_RATING, PRIOR_WEIGHT = 3.5, 3
CLOSEST_LIMIT = 4

TIER_TITLE, TIER_CATEGORY, TIER_DESCRIPTION, TIER_MEANING = 3, 2, 1, 0


@dataclass
class SearchHit:
    product: Product
    score: float  # keyword share + meaning, for ordering within a tier
    semantic: float
    keyword: bool  # matched by words (title/description/category), not only by meaning
    tier: int = TIER_MEANING


@dataclass
class SearchResult:
    hits: list[SearchHit]
    parsed: ParsedQuery
    closest: list[SearchHit] = field(default_factory=list)  # nothing fit the budget: nearest prices


def _word_pattern(term: str) -> str:
    """Whole word with an optional plural: "mat" matches "Mat"/"mats", never "Basmati"/"Mathematics"."""
    return rf"\m{re.escape(term)}(s|es)?\M"


def _matches(term: str, text: str) -> bool:
    return re.search(rf"\b{re.escape(term)}(s|es)?\b", text, re.IGNORECASE) is not None


def _share(concepts: list[tuple[str, ...]], text: str) -> float:
    """Share of the shopper's words found in ``text`` (a word counts if any of its synonyms is there)."""
    if not concepts:
        return 0.0
    return sum(any(_matches(t, text) for t in group) for group in concepts) / len(concepts)


def _description_counts(hit: SearchHit, concepts: list[tuple[str, ...]], has_matches: bool) -> bool:
    share = _share(concepts, f"{hit.product.title} {hit.product.description}")
    if share == 1.0:
        return True  # every word is there
    return not has_matches and share >= 0.5 and hit.semantic >= PARTIAL_DESCRIPTION_MIN_SIMILARITY


async def search(
    db: AsyncSession,
    query: str,
    *,
    category: str | None = None,
    max_price: Decimal | None = None,
    in_stock_only: bool = False,
    smart: bool = True,
    limit: int = 20,
) -> SearchResult:
    """``category``/``max_price`` given explicitly always win over what's read from the text.
    ``smart=False`` ignores budgets, sort words and category words found in the text."""
    parsed = parse_query(query)
    if not smart:
        parsed.min_price = parsed.max_price = None
        parsed.sort = "relevance"
        parsed.categories = set()
    if max_price is not None:
        parsed.max_price = max_price
    if not query.strip():
        return SearchResult([], parsed)

    filters = []
    if category:
        filters.append(Product.category == category.strip().lower())
    if in_stock_only:
        filters.append(Product.stock > 0)

    hits: dict[int, SearchHit] = {}

    # 1) Meaning: nearest neighbours of the cleaned, translated query. If the embedding model is
    #    unavailable (e.g. offline before its first download), keyword search still works.
    try:
        [query_vector] = await embed_texts([parsed.text])
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

    # 2) Words and categories.
    word_match = [
        or_(Product.title.op("~*")(_word_pattern(t)), Product.description.op("~*")(_word_pattern(t)))
        for t in parsed.terms
    ]
    if parsed.categories:
        word_match.append(Product.category.in_(parsed.categories))
    if word_match:
        keyword_stmt = (
            select(Product).where(or_(*word_match), *filters).options(selectinload(Product.seller)).limit(CANDIDATES * 2)
        )
        for product in (await db.execute(keyword_stmt)).scalars().all():
            hits.setdefault(product.id, SearchHit(product, 0.0, 0.0, keyword=False))

    # 3) Tiers.
    for hit in hits.values():
        p = hit.product
        title_share = _share(parsed.concepts, p.title)
        text_share = _share(parsed.concepts, f"{p.title} {p.description}")
        if title_share > 0:
            hit.tier = TIER_TITLE
        elif p.category in parsed.categories:
            hit.tier = TIER_CATEGORY
        elif text_share > 0:
            hit.tier = TIER_DESCRIPTION
        hit.keyword = hit.tier > TIER_MEANING
        hit.score = text_share + title_share + hit.semantic

    has_matches = any(h.tier >= TIER_CATEGORY for h in hits.values())
    best_semantic = max((h.semantic for h in hits.values()), default=0.0)
    meaning_cutoff = max(MIN_SIMILARITY_WITH_MATCHES if has_matches else MIN_SIMILARITY, best_semantic * RELATIVE_CUTOFF)
    relevant = [
        h
        for h in hits.values()
        if h.tier >= TIER_CATEGORY
        or (h.tier == TIER_DESCRIPTION and _description_counts(h, parsed.concepts, has_matches))
        or h.semantic >= meaning_cutoff
    ]

    # 4) Order: tier first, then in-stock, then what the shopper asked for.
    ratings = await rating_summaries(db, [h.product.id for h in relevant]) if parsed.sort == "rating" else {}

    def bayes(h: SearchHit) -> float:
        r = ratings.get(h.product.id)
        n, avg = (r.count, r.average or 0.0) if r else (0, 0.0)
        return (PRIOR_RATING * PRIOR_WEIGHT + avg * n) / (PRIOR_WEIGHT + n)

    def key(h: SearchHit) -> tuple:
        base = (h.tier, h.product.stock > 0)
        if parsed.sort == "rating":
            return (*base, round(_share(parsed.concepts, h.product.title), 1), bayes(h), h.score)
        if parsed.sort == "price_asc":
            return (*base, -price_of(h.product).final_price)
        return (*base, h.score)

    relevant.sort(key=key, reverse=True)

    def in_budget(h: SearchHit) -> bool:
        price = price_of(h.product).final_price
        return (parsed.max_price is None or price <= parsed.max_price) and (parsed.min_price is None or price >= parsed.min_price)

    fitting = [h for h in relevant if in_budget(h)]
    closest: list[SearchHit] = []
    if not fitting and relevant and (parsed.max_price is not None or parsed.min_price is not None):
        target = parsed.max_price if parsed.max_price is not None else parsed.min_price
        top_tier = max(h.tier for h in relevant)  # e.g. only kurtas, not "pairs with kurtas" items
        closest = sorted(
            (h for h in relevant if h.tier == top_tier),
            key=lambda h: abs(price_of(h.product).final_price - target),
        )[:CLOSEST_LIMIT]
    return SearchResult(fitting[:limit], parsed, closest)


async def search_products(
    db: AsyncSession,
    query: str,
    *,
    category: str | None = None,
    max_price: Decimal | None = None,
    in_stock_only: bool = False,
    limit: int = 20,
) -> list[SearchHit]:
    """Just the hits (used by the shopping assistant's search tool)."""
    result = await search(
        db, query, category=category, max_price=max_price, in_stock_only=in_stock_only, limit=limit
    )
    return result.hits
