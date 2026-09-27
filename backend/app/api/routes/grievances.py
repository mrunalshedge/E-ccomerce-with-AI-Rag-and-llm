from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.ai.llm import AssistantModels, get_assistant_models
from app.api.deps import CurrentUser, CustomerUser, DbSession
from app.schemas.grievance import GrievanceComment, GrievanceCreate, GrievanceRead
from app.services import grievance_service
from app.services.grievance_service import to_grievance_read

router = APIRouter(prefix="/grievances", tags=["grievances"])


@router.post("", response_model=GrievanceRead, status_code=status.HTTP_201_CREATED)
async def raise_grievance(
    data: GrievanceCreate,
    user: CustomerUser,
    db: DbSession,
    models: Annotated[AssistantModels | None, Depends(get_assistant_models)],
) -> GrievanceRead:
    """Raise a complaint (optionally about one of your orders). It's acknowledged instantly:
    simple information requests are answered by AI (`ai_resolved`, reopenable); anything that
    needs action goes to the grievance team (`open`), to be resolved within one month."""
    return to_grievance_read(await grievance_service.create_grievance(db, user, models, data))


@router.get("", response_model=list[GrievanceRead])
async def my_grievances(user: CustomerUser, db: DbSession) -> list[GrievanceRead]:
    return [to_grievance_read(g) for g in await grievance_service.list_mine(db, user)]


@router.get("/{grievance_id}", response_model=GrievanceRead)
async def get_grievance(grievance_id: int, user: CurrentUser, db: DbSession) -> GrievanceRead:
    return to_grievance_read(await grievance_service.get_for_user(db, user, grievance_id))


@router.post("/{grievance_id}/comments", response_model=GrievanceRead)
async def add_comment(grievance_id: int, data: GrievanceComment, user: CustomerUser, db: DbSession) -> GrievanceRead:
    """Add details to an open complaint."""
    return to_grievance_read(await grievance_service.add_customer_comment(db, user, grievance_id, data.message))


@router.post("/{grievance_id}/reopen", response_model=GrievanceRead)
async def reopen(grievance_id: int, data: GrievanceComment, user: CustomerUser, db: DbSession) -> GrievanceRead:
    """"This didn't help": hand an answered complaint to a person (within 14 days)."""
    return to_grievance_read(await grievance_service.reopen(db, user, grievance_id, data.message))
