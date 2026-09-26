"""Tools the shopping assistant can call. They read live data (RAG): the model never answers
prices, stock or order status from memory.

Tools are built per request so they share the request's DB session and know who is asking.
Every product a tool shows the model is recorded, so the API can return real product cards.
"""

import json
from dataclasses import dataclass, field
from decimal import Decimal

from langchain_core.tools import BaseTool, tool
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.errors import NotFoundError
from app.core.policies import RETURN_WINDOW_DAYS
from app.models.product import Product
from app.models.review import Review, ReviewStatus, ReviewSummary
from app.models.user import User, UserRole
from app.services import order_service, search_service
from app.services.product_service import price_of
from app.services.rating_service import rating_distribution, rating_summaries


@dataclass
class ToolContext:
    db: AsyncSession
    user: User | None
    # (id, title) of products shown to the model, most relevant first (details before search hits).
    details: list[tuple[int, str]] = field(default_factory=list)
    search_hits: list[tuple[int, str]] = field(default_factory=list)

    def surfaced_products(self, limit: int = 6) -> list[tuple[int, str]]:
        return list(dict.fromkeys(self.details + self.search_hits))[:limit]


def _dump(data: object) -> str:
    return json.dumps(data, ensure_ascii=False, default=str)


def _summary(product: Product) -> dict:
    price = price_of(product)
    return {
        "id": product.id,
        "title": product.title,
        "category": product.category,
        "final_price_inr": str(price.final_price),
        "free_delivery": price.delivery_fee == 0,
        "in_stock": product.stock > 0,
        "returnable": product.is_returnable,
        "seller": product.seller.business_name,
        "seller_trust_score": round(product.seller.trust_score),
    }


def build_tools(ctx: ToolContext) -> list[BaseTool]:
    @tool
    async def search_products(query: str, max_price_inr: float | None = None, category: str | None = None) -> str:
        """Search the ShopSense catalogue by meaning and keywords.

        Args:
            query: What the customer wants, rewritten as a short ENGLISH product search phrase
                (translate Hindi/Marathi/Hinglish first, e.g. "gaana sunne ke liye" -> "earphones").
            max_price_inr: Optional budget: maximum all-inclusive price in rupees.
            category: Optional: one of clothing, home, grocery, electronics, books.
        """
        hits = await search_service.search_products(
            ctx.db,
            query,
            category=category,
            max_price=Decimal(str(max_price_inr)) if max_price_inr else None,
            limit=5,
        )
        ctx.search_hits.extend((h.product.id, h.product.title) for h in hits)
        if not hits:
            return "No matching products. Tell the customer honestly; suggest another search."
        return _dump([_summary(h.product) for h in hits])

    @tool
    async def get_product_details(product_id: int) -> str:
        """Full details for one product: description, the complete price breakdown (base price,
        delivery, platform fee, GST, final price), stock, return policy and seller disclosure."""
        stmt = select(Product).where(Product.id == product_id).options(selectinload(Product.seller))
        product = (await ctx.db.execute(stmt)).scalar_one_or_none()
        if product is None:
            return f"Product {product_id} does not exist."
        ctx.details.append((product.id, product.title))
        seller = product.seller
        return _dump(
            {
                **_summary(product),
                "description": product.description,
                "stock": product.stock,
                "country_of_origin": product.country_of_origin,
                "price_breakdown_inr": price_of(product).model_dump(exclude={"currency"}),
                "seller_details": {
                    "address": seller.address,
                    "gstin": seller.gstin,
                    "grievance_officer": f"{seller.grievance_officer_name} <{seller.grievance_officer_email}>",
                },
            }
        )

    @tool
    async def get_review_insights(product_id: int) -> str:
        """What verified buyers say about a product: average rating, star distribution, the AI
        summary of reviews (if one exists) and a few recent reviews. Use for questions like
        "is it good?", "what do people say?", "quality kaisi hai?"."""
        if await ctx.db.get(Product, product_id) is None:
            return f"Product {product_id} does not exist."
        rating = (await rating_summaries(ctx.db, [product_id]))[product_id]
        if rating.count == 0:
            return "This product has no published reviews yet."
        summaries = (
            await ctx.db.execute(select(ReviewSummary).where(ReviewSummary.product_id == product_id))
        ).scalars().all()
        summary = next((s.summary for s in summaries if s.language == "en"), summaries[0].summary if summaries else None)
        recent = (
            await ctx.db.execute(
                select(Review)
                .where(Review.product_id == product_id, Review.status == ReviewStatus.PUBLISHED)
                .order_by(Review.created_at.desc())
                .limit(3)
            )
        ).scalars().all()
        return _dump(
            {
                "average_rating": rating.average,
                "review_count": rating.count,
                "star_distribution": await rating_distribution(ctx.db, product_id),
                "ai_summary": summary,
                "recent_reviews": [f"{r.rating}★ {r.body[:200]}" for r in recent],
                "note": "All reviews are from verified purchases; suspected fake reviews are excluded.",
            }
        )

    @tool
    def get_return_policy() -> str:
        """ShopSense's return and refund rules."""
        return (
            f"Returns are requested from the order page within {RETURN_WINDOW_DAYS} days of delivery. "
            "Wrong items and fake/counterfeit items are ALWAYS accepted in that window, even for "
            "products marked non-returnable. Damaged or other reasons are accepted only for returnable "
            "products. An admin reviews each request; approved wrong/fake returns lower the seller's "
            "trust score. Orders can be cancelled free of charge until they ship; prepaid amounts are refunded."
        )

    @tool
    async def get_my_orders() -> str:
        """The logged-in customer's recent orders with status and totals."""
        if ctx.user is None or ctx.user.role != UserRole.CUSTOMER:
            return "The user is not logged in as a customer. Ask them to log in to see their orders."
        orders = (await order_service.list_customer_orders(ctx.db, ctx.user))[:5]
        if not orders:
            return "This customer has no orders yet."
        return _dump(
            [
                {
                    "order_id": o.id,
                    "status": o.status.value,
                    "payment": f"{o.payment_method.value} ({o.payment_status.value})",
                    "total_inr": str(o.grand_total),
                    "items": [f"{i.title} x{i.quantity}" for i in o.items],
                    "placed_on": o.created_at.date().isoformat(),
                    "latest_update": o.events[-1].note if o.events else None,
                }
                for o in orders
            ]
        )

    @tool
    async def get_order_status(order_id: int) -> str:
        """Status timeline for one of the logged-in customer's orders."""
        if ctx.user is None or ctx.user.role != UserRole.CUSTOMER:
            return "The user is not logged in as a customer. Ask them to log in to check an order."
        try:
            order = await order_service.get_order_for_user(ctx.db, ctx.user, order_id)
        except NotFoundError:
            return f"Order {order_id} was not found for this customer."
        return _dump(
            {
                "order_id": order.id,
                "status": order.status.value,
                "delivered_at": order.delivered_at,
                "timeline": [{"status": e.status.value, "at": e.created_at, "note": e.note} for e in order.events],
            }
        )

    return [
        search_products,
        get_product_details,
        get_review_insights,
        get_return_policy,
        get_my_orders,
        get_order_status,
    ]
