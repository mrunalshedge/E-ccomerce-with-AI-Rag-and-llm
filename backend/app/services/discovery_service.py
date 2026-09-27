"""Discovery features built on app/dsa: autocomplete (trie), frequently bought together
(co-purchase graph), recently viewed (LRU) and recommendations (heap top-K).

The trie and graph are built from the database and cached in memory with a short TTL (and
invalidated when products or orders change), so requests don't rebuild them.
"""

import asyncio
import math
import time
from collections import Counter, defaultdict
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import timedelta
from typing import Generic, TypeVar

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.dsa.graph import CoPurchaseGraph
from app.dsa.lru import LRUCache
from app.dsa.topk import top_k
from app.dsa.trie import Suggestion, Trie
from app.models.order import Order, OrderItem, OrderStatus
from app.models.product import Product
from app.models.seller import Seller
from app.models.user import User
from app.services.rating_service import rating_summaries

T = TypeVar("T")


class Cached(Generic[T]):
    """Rebuild-on-expiry cache for one expensive in-memory structure (one build at a time)."""

    def __init__(self, ttl_seconds: float) -> None:
        self.ttl = ttl_seconds
        self._value: T | None = None
        self._built_at = 0.0
        self._lock = asyncio.Lock()

    async def get(self, build: Callable[[], Awaitable[T]]) -> T:
        if self._value is None or time.monotonic() - self._built_at > self.ttl:
            async with self._lock:
                if self._value is None or time.monotonic() - self._built_at > self.ttl:
                    self._value = await build()
                    self._built_at = time.monotonic()
        return self._value

    def invalidate(self) -> None:
        self._value = None


_trie_cache: Cached[Trie] = Cached(ttl_seconds=300)
_graph_cache: Cached[CoPurchaseGraph] = Cached(ttl_seconds=120)


def invalidate_catalogue() -> None:
    """Call after products change (new titles for autocomplete)."""
    _trie_cache.invalidate()


def invalidate_orders() -> None:
    """Call after checkouts/cancellations (co-purchase edges, popularity)."""
    _graph_cache.invalidate()
    _trie_cache.invalidate()  # popularity weights


async def _units_sold(db: AsyncSession) -> dict[int, int]:
    stmt = (
        select(OrderItem.product_id, func.sum(OrderItem.quantity))
        .join(Order, Order.id == OrderItem.order_id)
        .where(Order.status != OrderStatus.CANCELLED, OrderItem.product_id.is_not(None))
        .group_by(OrderItem.product_id)
    )
    return {pid: int(n) for pid, n in (await db.execute(stmt)).all()}


# ---------- autocomplete (trie) ----------


async def _build_trie(db: AsyncSession) -> Trie:
    products = (await db.execute(select(Product.id, Product.title, Product.category))).all()
    sold = await _units_sold(db)
    ratings = await rating_summaries(db, [p.id for p in products])
    trie = Trie(k=8)
    categories: Counter[str] = Counter()
    for pid, title, category in products:
        rating = ratings[pid]
        weight = 1 + 2 * sold.get(pid, 0) + 0.5 * rating.count + ((rating.average or 3) - 3)
        suggestion = Suggestion(weight, title, "product", pid)
        words = title.split()
        for i in range(len(words)):  # "Handwoven Cotton Kurta", "Cotton Kurta", "Kurta"
            trie.insert(" ".join(words[i:]), suggestion)
        categories[category] += 1
    for category, count in categories.items():
        trie.insert(category, Suggestion(100 + count, category, "category", category))  # categories first
    for seller_id, name in (await db.execute(select(Seller.id, Seller.business_name))).all():
        trie.insert(name, Suggestion(0.5, name, "seller", seller_id))
    return trie


async def suggest(db: AsyncSession, prefix: str, limit: int) -> list[Suggestion]:
    prefix = " ".join(prefix.split())  # collapse whitespace
    if not prefix:
        return []
    trie = await _trie_cache.get(lambda: _build_trie(db))
    return trie.complete(prefix, limit)


# ---------- frequently bought together (graph) ----------

SAME_CHECKOUT = timedelta(minutes=2)


async def _build_graph(db: AsyncSession) -> CoPurchaseGraph:
    rows = (
        await db.execute(
            select(Order.user_id, Order.created_at, OrderItem.product_id)
            .join(OrderItem, OrderItem.order_id == Order.id)
            .where(Order.status != OrderStatus.CANCELLED, OrderItem.product_id.is_not(None))
            .order_by(Order.user_id, Order.created_at)
        )
    ).all()
    graph = CoPurchaseGraph()
    by_customer: defaultdict[int, set[int]] = defaultdict(set)
    checkouts: list[tuple[int, object, set[int]]] = []  # (user, started_at, products)
    for user_id, created_at, product_id in rows:
        by_customer[user_id].add(product_id)
        # Checkout splits a cart into one order per seller, all created moments apart.
        if checkouts and checkouts[-1][0] == user_id and created_at - checkouts[-1][1] <= SAME_CHECKOUT:  # type: ignore[operator]
            checkouts[-1][2].add(product_id)
        else:
            checkouts.append((user_id, created_at, {product_id}))
    for products in by_customer.values():
        graph.add_basket(products)  # same customer bought both: weight 1
    for _, _, products in checkouts:
        graph.add_basket(products)  # same cart: +1 more
    return graph


async def get_graph(db: AsyncSession) -> CoPurchaseGraph:
    return await _graph_cache.get(lambda: _build_graph(db))


async def _in_stock(db: AsyncSession, ids: list[int]) -> list[Product]:
    if not ids:
        return []
    stmt = select(Product).where(Product.id.in_(ids), Product.stock > 0).options(selectinload(Product.seller))
    by_id = {p.id: p for p in (await db.execute(stmt)).scalars().all()}
    return [by_id[i] for i in ids if i in by_id]


async def bought_together(db: AsyncSession, product_id: int, limit: int) -> list[Product]:
    graph = await get_graph(db)
    ranked = graph.recommend(product_id, k=limit * 2)  # extra, in case some are out of stock
    return (await _in_stock(db, [pid for pid, _ in ranked]))[:limit]


# ---------- recently viewed (LRU of LRUs) ----------


class RecentlyViewed:
    """Per-user recently viewed products. The outer LRU bounds memory to the most recently active
    users; each inner LRU keeps a user's last ``per_user`` products. All operations O(1)."""

    def __init__(self, users: int = 10_000, per_user: int = 12) -> None:
        self._users: LRUCache[int, LRUCache[int, float]] = LRUCache(users)
        self.per_user = per_user

    def record(self, user_id: int, product_id: int) -> None:
        history = self._users.get(user_id) or LRUCache(self.per_user)
        history.put(product_id, time.time())
        self._users.put(user_id, history)

    def product_ids(self, user_id: int) -> list[int]:
        history = self._users.get(user_id)
        return list(history.keys()) if history else []


recently_viewed = RecentlyViewed()


async def recently_viewed_products(db: AsyncSession, user: User) -> list[Product]:
    ids = recently_viewed.product_ids(user.id)
    if not ids:
        return []
    stmt = select(Product).where(Product.id.in_(ids)).options(selectinload(Product.seller))
    by_id = {p.id: p for p in (await db.execute(stmt)).scalars().all()}
    return [by_id[i] for i in ids if i in by_id]


# ---------- recommendations (heap top-K) ----------


@dataclass(frozen=True)
class Recommendation:
    product: Product
    score: float
    reason: str  # "bought_together" | "similar_interest" | "popular"


async def recommend(db: AsyncSession, user: User | None, seen_ids: list[int], limit: int) -> list[Recommendation]:
    """Score every in-stock candidate, then keep the best ``limit`` with a bounded heap.

    score = 1.5 × co-purchase links to what you bought/viewed
          + 1.0 × your interest in the product's category
          + 0.3 × log(1 + units sold) + 0.3 × (rating − 3)
    Guests get the same with only the products they viewed (sent from the browser), or pure
    popularity when there's no history at all."""
    purchased: set[int] = set()
    if user is not None:
        purchased = set(
            (
                await db.execute(
                    select(OrderItem.product_id)
                    .join(Order, Order.id == OrderItem.order_id)
                    .where(Order.user_id == user.id, Order.status != OrderStatus.CANCELLED, OrderItem.product_id.is_not(None))
                )
            ).scalars().all()
        )
        seen_ids = [*recently_viewed.product_ids(user.id), *seen_ids]
    anchors = purchased | set(seen_ids)

    candidates = list(
        (await db.execute(select(Product).where(Product.stock > 0).options(selectinload(Product.seller)))).scalars().all()
    )
    categories_by_id = {p.id: p.category for p in candidates}
    if anchors - categories_by_id.keys():
        for pid, category in (await db.execute(select(Product.id, Product.category).where(Product.id.in_(anchors)))).all():
            categories_by_id[pid] = category
    interest = Counter(categories_by_id[a] for a in anchors if a in categories_by_id)
    top_interest = max(interest.values(), default=1)

    graph = await get_graph(db)
    sold = await _units_sold(db)
    ratings = await rating_summaries(db, [p.id for p in candidates])

    def scored(product: Product) -> Recommendation:
        co = sum(graph.weight(product.id, a) for a in anchors)
        affinity = interest.get(product.category, 0) / top_interest
        rating = ratings[product.id]
        base = 0.3 * math.log1p(sold.get(product.id, 0)) + (0.3 * (rating.average - 3) if rating.average else 0.0)
        reason = "bought_together" if co else "similar_interest" if affinity else "popular"
        return Recommendation(product, 1.5 * co + affinity + base, reason)

    pool = (scored(p) for p in candidates if p.id not in anchors)
    return top_k(pool, limit, key=lambda r: r.score)
