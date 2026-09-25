from fastapi import APIRouter, status

from app.api.deps import CurrentUser, CustomerUser, DbSession
from app.schemas.order import CheckoutRequest, CheckoutResponse, OrderRead
from app.services import order_service
from app.services.order_service import to_order_read

router = APIRouter(prefix="/orders", tags=["orders"])


@router.post("", response_model=CheckoutResponse, status_code=status.HTTP_201_CREATED)
async def checkout(data: CheckoutRequest, user: CustomerUser, db: DbSession) -> CheckoutResponse:
    """Place an order for everything in the cart.

    - ``payment_method`` is required (upi / card / cod); it is never chosen or changed for you.
    - ``expected_total`` must equal the cart's ``totals.grand_total``; if prices or stock changed,
      you get **409** and nothing is charged.
    - The cart is split into one order per seller.
    """
    orders = await order_service.checkout(db, user, data)
    return CheckoutResponse(
        orders=[to_order_read(o) for o in orders],
        grand_total=sum((o.grand_total for o in orders)),
    )


@router.get("", response_model=list[OrderRead])
async def list_my_orders(user: CustomerUser, db: DbSession) -> list[OrderRead]:
    return [to_order_read(o) for o in await order_service.list_customer_orders(db, user)]


@router.get("/{order_id}", response_model=OrderRead)
async def get_order(order_id: int, user: CurrentUser, db: DbSession) -> OrderRead:
    """Order details with the status timeline. Visible to its customer, its seller and admins."""
    return to_order_read(await order_service.get_order_for_user(db, user, order_id))


@router.post("/{order_id}/cancel", response_model=OrderRead)
async def cancel_order(order_id: int, user: CustomerUser, db: DbSession) -> OrderRead:
    """Cancel before shipping. Stock is restored and prepaid amounts are refunded."""
    return to_order_read(await order_service.cancel_order(db, user, order_id))
