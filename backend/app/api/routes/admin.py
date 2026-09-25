from typing import Annotated

from fastapi import APIRouter, Query

from app.api.deps import AdminUser, DbSession
from app.models.returns import ReturnStatus
from app.schemas.returns import ReturnRead, ReturnResolve
from app.services import return_service
from app.services.return_service import to_return_read

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/returns", response_model=list[ReturnRead])
async def list_returns(
    _: AdminUser, db: DbSession, status: Annotated[ReturnStatus | None, Query()] = None
) -> list[ReturnRead]:
    return [to_return_read(r) for r in await return_service.list_all_returns(db, status)]


@router.post("/returns/{return_id}/resolve", response_model=ReturnRead)
async def resolve_return(return_id: int, data: ReturnResolve, admin: AdminUser, db: DbSession) -> ReturnRead:
    """Approve or reject a return. Approving a wrong-item or counterfeit return lowers the
    seller's trust score by 5."""
    return to_return_read(await return_service.resolve_return(db, admin, return_id, data))
