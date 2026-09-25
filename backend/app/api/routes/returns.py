from fastapi import APIRouter, status

from app.api.deps import CustomerUser, DbSession
from app.schemas.returns import ReturnCreate, ReturnRead
from app.services import return_service
from app.services.return_service import to_return_read

router = APIRouter(prefix="/returns", tags=["returns"])


@router.post("", response_model=ReturnRead, status_code=status.HTTP_201_CREATED)
async def request_return(data: ReturnCreate, user: CustomerUser, db: DbSession) -> ReturnRead:
    """Request a return for a delivered item, within 7 days of delivery.

    ``wrong_item`` and ``counterfeit`` are always accepted, even for non-returnable products.
    """
    return to_return_read(await return_service.create_return(db, user, data))


@router.get("", response_model=list[ReturnRead])
async def list_my_returns(user: CustomerUser, db: DbSession) -> list[ReturnRead]:
    return [to_return_read(r) for r in await return_service.list_customer_returns(db, user)]
