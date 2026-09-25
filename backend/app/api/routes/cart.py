from fastapi import APIRouter

from app.api.deps import CustomerUser, DbSession
from app.schemas.cart import CartItemAdd, CartItemUpdate, CartRead
from app.services import cart_service

router = APIRouter(prefix="/cart", tags=["cart"])


@router.get("", response_model=CartRead)
async def get_cart(user: CustomerUser, db: DbSession) -> CartRead:
    """Your cart with live all-inclusive prices. ``totals.grand_total`` is what checkout charges."""
    return await cart_service.get_cart(db, user)


@router.post("/items", response_model=CartRead)
async def add_item(data: CartItemAdd, user: CustomerUser, db: DbSession) -> CartRead:
    """Add a product (or increase its quantity if it's already in the cart)."""
    return await cart_service.add_item(db, user, data)


@router.patch("/items/{product_id}", response_model=CartRead)
async def update_item(product_id: int, data: CartItemUpdate, user: CustomerUser, db: DbSession) -> CartRead:
    return await cart_service.update_quantity(db, user, product_id, data.quantity)


@router.delete("/items/{product_id}", response_model=CartRead)
async def remove_item(product_id: int, user: CustomerUser, db: DbSession) -> CartRead:
    return await cart_service.remove_item(db, user, product_id)
