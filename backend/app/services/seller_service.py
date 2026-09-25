from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ConflictError
from app.models.seller import Seller
from app.models.user import User
from app.schemas.seller import SellerCreate


async def get_seller_by_user_id(db: AsyncSession, user_id: int) -> Seller | None:
    result = await db.execute(select(Seller).where(Seller.user_id == user_id))
    return result.scalar_one_or_none()


async def create_seller_profile(db: AsyncSession, user: User, data: SellerCreate) -> Seller:
    """Create the (single) seller profile for ``user``."""
    if await get_seller_by_user_id(db, user.id) is not None:
        raise ConflictError("Seller profile already exists")

    seller = Seller(user_id=user.id, **data.model_dump())
    db.add(seller)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise ConflictError("Seller profile already exists") from exc
    return seller
