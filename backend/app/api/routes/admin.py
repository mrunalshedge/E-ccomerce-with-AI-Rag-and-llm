from typing import Annotated

from fastapi import APIRouter, Query

from app.api.deps import AdminUser, DbSession
from app.models.grievance import GrievanceStatus
from app.models.product import Product
from app.models.returns import ReturnStatus
from app.models.review import Review, ReviewStatus
from app.schemas.grievance import AdminGrievanceRead, AdminOverview, GrievanceAdminUpdate
from app.schemas.returns import ReturnRead, ReturnResolve
from app.schemas.review import AdminReviewRead, ReviewModerate
from app.services import grievance_service, return_service, review_service
from app.services.grievance_service import to_admin_read
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


def _admin_review(review: Review, product_title: str) -> AdminReviewRead:
    return AdminReviewRead(
        **review_service.to_review_read(review).model_dump(),
        suspicion_score=review.suspicion_score,
        suspicion_reasons=review.suspicion_reasons,
        moderation_note=review.moderation_note,
        product_title=product_title,
    )


@router.get("/reviews", response_model=list[AdminReviewRead])
async def list_reviews(
    _: AdminUser, db: DbSession, status: Annotated[ReviewStatus | None, Query()] = ReviewStatus.FLAGGED
) -> list[AdminReviewRead]:
    """Reviews for moderation, most suspicious first (defaults to the flagged queue), with the
    detection signals that tripped."""
    return [_admin_review(r, title) for r, title in await review_service.list_for_moderation(db, status)]


@router.post("/reviews/{review_id}/moderate", response_model=AdminReviewRead)
async def moderate_review(review_id: int, data: ReviewModerate, _: AdminUser, db: DbSession) -> AdminReviewRead:
    """Approve (publish) a flagged review, or remove a fake/abusive one. Trust scores update."""
    review = await review_service.moderate(db, review_id, data)
    product = await db.get(Product, review.product_id)
    return _admin_review(review, product.title if product else "")


@router.get("/overview", response_model=AdminOverview)
async def overview(_: AdminUser, db: DbSession) -> AdminOverview:
    """Headline numbers for the admin dashboard."""
    return AdminOverview(**await grievance_service.overview(db))


@router.get("/grievances", response_model=list[AdminGrievanceRead])
async def list_grievances(
    _: AdminUser,
    db: DbSession,
    status: Annotated[GrievanceStatus | None, Query()] = None,
    open_only: bool = True,
) -> list[AdminGrievanceRead]:
    """The complaints queue: most urgent first, then by resolution deadline."""
    return [to_admin_read(g, u) for g, u in await grievance_service.list_for_admin(db, status, open_only)]


@router.post("/grievances/{grievance_id}/update", response_model=AdminGrievanceRead)
async def update_grievance(
    grievance_id: int, data: GrievanceAdminUpdate, admin: AdminUser, db: DbSession
) -> AdminGrievanceRead:
    """Mark a complaint in progress or resolved, with a note the customer will see."""
    grievance, customer = await grievance_service.admin_update(db, admin, grievance_id, data)
    return to_admin_read(grievance, customer)
