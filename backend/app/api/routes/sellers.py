from fastapi import APIRouter, status

from app.api.deps import CurrentSeller, DbSession, SellerUser
from app.core.policies import TRUST_MIN_REVIEWS, TRUST_RATING_TARGET
from app.schemas.order import OrderRead, OrderStatusUpdate
from app.schemas.product import ProductRead, ProductUpdate
from app.schemas.returns import ReturnRead
from app.schemas.seller import SellerCreate, SellerDashboard, SellerRead, SellerReviewRead, TrustBreakdownRead
from app.services import (
    discovery_service,
    order_service,
    product_service,
    return_service,
    seller_dashboard_service,
    seller_service,
)
from app.services.order_service import to_order_read
from app.services.return_service import to_return_read
from app.services.review_service import reviewer_name
from app.services.trust_service import trust_breakdown

router = APIRouter(prefix="/sellers", tags=["sellers"])


@router.post("/me", response_model=SellerRead, status_code=status.HTTP_201_CREATED)
async def create_my_seller_profile(data: SellerCreate, user: SellerUser, db: DbSession) -> SellerRead:
    """Create the seller profile for the logged-in seller (one per account)."""
    seller = await seller_service.create_seller_profile(db, user, data)
    return SellerRead.model_validate(seller)


@router.get("/me", response_model=SellerRead)
async def get_my_seller_profile(seller: CurrentSeller) -> SellerRead:
    return SellerRead.model_validate(seller)


@router.get("/me/orders", response_model=list[OrderRead])
async def list_my_orders(seller: CurrentSeller, db: DbSession) -> list[OrderRead]:
    """Orders you need to fulfil."""
    return [to_order_read(o) for o in await order_service.list_seller_orders(db, seller)]


@router.patch("/me/orders/{order_id}/status", response_model=OrderRead)
async def update_order_status(
    order_id: int, data: OrderStatusUpdate, seller: CurrentSeller, user: SellerUser, db: DbSession
) -> OrderRead:
    """Move an order forward: placed → shipped → delivered."""
    return to_order_read(await order_service.update_status_by_seller(db, seller, user, order_id, data))


@router.get("/me/returns", response_model=list[ReturnRead])
async def list_my_returns(seller: CurrentSeller, db: DbSession) -> list[ReturnRead]:
    """Return requests against items you sold."""
    return [to_return_read(r) for r in await return_service.list_seller_returns(db, seller)]


@router.get("/me/products", response_model=list[ProductRead])
async def my_products(seller: CurrentSeller, db: DbSession) -> list[ProductRead]:
    """All your products (including out of stock), lowest stock first."""
    return await product_service.to_product_reads(db, await seller_dashboard_service.list_products(db, seller))


@router.patch("/me/products/{product_id}", response_model=ProductRead)
async def update_my_product(product_id: int, data: ProductUpdate, seller: CurrentSeller, db: DbSession) -> ProductRead:
    """Edit your product. Price changes apply to new carts; customers with an older price in their
    cart are asked to confirm the new total at checkout (it's never charged silently)."""
    product = await seller_dashboard_service.update_product(db, seller, product_id, data)
    discovery_service.invalidate_catalogue()
    return (await product_service.to_product_reads(db, [product]))[0]


@router.get("/me/dashboard", response_model=SellerDashboard)
async def my_dashboard(seller: CurrentSeller, db: DbSession) -> SellerDashboard:
    """Headline numbers plus how your trust score is calculated."""
    breakdown = await trust_breakdown(db, seller.id)
    return SellerDashboard(
        **await seller_dashboard_service.dashboard(db, seller),
        trust=TrustBreakdownRead(
            **breakdown.__dict__,
            min_reviews_for_rating_penalty=TRUST_MIN_REVIEWS,
            rating_target=TRUST_RATING_TARGET,
        ),
    )


@router.get("/me/reviews", response_model=list[SellerReviewRead])
async def my_reviews(seller: CurrentSeller, db: DbSession) -> list[SellerReviewRead]:
    """Recent published reviews of your products."""
    return [
        SellerReviewRead(
            id=r.id,
            product_id=r.product_id,
            product_title=title,
            rating=r.rating,
            title=r.title,
            body=r.body,
            reviewer=reviewer_name(r.user),
            created_at=r.created_at,
        )
        for r, title in await seller_dashboard_service.recent_reviews(db, seller)
    ]
