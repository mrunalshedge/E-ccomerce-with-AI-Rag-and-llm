from fastapi import APIRouter, status

from app.api.deps import DbSession, SellerUser
from app.core.errors import NotFoundError
from app.schemas.seller import SellerCreate, SellerRead
from app.services import seller_service

router = APIRouter(prefix="/sellers", tags=["sellers"])


@router.post("/me", response_model=SellerRead, status_code=status.HTTP_201_CREATED)
async def create_my_seller_profile(data: SellerCreate, user: SellerUser, db: DbSession) -> SellerRead:
    """Create the seller profile for the logged-in seller (one per account)."""
    seller = await seller_service.create_seller_profile(db, user, data)
    return SellerRead.model_validate(seller)


@router.get("/me", response_model=SellerRead)
async def get_my_seller_profile(user: SellerUser, db: DbSession) -> SellerRead:
    seller = await seller_service.get_seller_by_user_id(db, user.id)
    if seller is None:
        raise NotFoundError("You have not created a seller profile yet")
    return SellerRead.model_validate(seller)
