from fastapi import APIRouter, status

from app.api.deps import CurrentSeller, DbSession, SellerUser
from app.schemas.order import OrderRead, OrderStatusUpdate
from app.schemas.returns import ReturnRead
from app.schemas.seller import SellerCreate, SellerRead
from app.services import order_service, return_service, seller_service
from app.services.order_service import to_order_read
from app.services.return_service import to_return_read

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
