"""Grievance lifecycle: create (+ AI triage), comment, reopen, and team updates."""

from datetime import timedelta
from decimal import Decimal

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.ai.llm import AssistantModels
from app.ai.triage import triage
from app.core.errors import ConflictError, NotFoundError
from app.core.policies import GRIEVANCE_REOPEN_DAYS, GRIEVANCE_RESOLVE_DAYS
from app.db.types import utcnow
from app.models.grievance import (
    Grievance,
    GrievanceActor,
    GrievanceEvent,
    GrievancePriority,
    GrievanceStatus,
)
from app.models.order import Order, OrderItem, OrderStatus
from app.models.returns import ReturnRequest, ReturnStatus
from app.models.review import Review, ReviewStatus
from app.models.user import User, UserRole
from app.schemas.grievance import (
    AdminGrievanceRead,
    GrievanceAdminUpdate,
    GrievanceCreate,
    GrievanceEventRead,
    GrievanceRead,
)
from app.services import order_service

OPEN_STATES = (GrievanceStatus.OPEN, GrievanceStatus.IN_PROGRESS)
PRIORITY_RANK = case(
    {GrievancePriority.URGENT: 0, GrievancePriority.HIGH: 1, GrievancePriority.MEDIUM: 2, GrievancePriority.LOW: 3},
    value=Grievance.priority,
)


# ---------- responses ----------


def _can_reopen(g: Grievance) -> bool:
    closed_at = g.resolved_at or g.acknowledged_at
    return (
        g.status in (GrievanceStatus.AI_RESOLVED, GrievanceStatus.RESOLVED)
        and closed_at is not None
        and utcnow() - closed_at <= timedelta(days=GRIEVANCE_REOPEN_DAYS)
    )


def to_grievance_read(g: Grievance) -> GrievanceRead:
    """``g.events`` must be loaded."""
    return GrievanceRead(
        id=g.id,
        order_id=g.order_id,
        subject=g.subject,
        description=g.description,
        category=g.category,
        priority=g.priority,
        status=g.status,
        ai_reply=g.ai_reply,
        created_at=g.created_at,
        acknowledged_at=g.acknowledged_at,
        resolve_by=g.resolve_by,
        resolved_at=g.resolved_at,
        overdue=g.status in OPEN_STATES and utcnow() > g.resolve_by,
        can_reopen=_can_reopen(g),
        timeline=[GrievanceEventRead.model_validate(e) for e in g.events],
    )


def to_admin_read(g: Grievance, customer: User) -> AdminGrievanceRead:
    return AdminGrievanceRead(
        **to_grievance_read(g).model_dump(),
        customer_name=customer.name,
        customer_email=customer.email,
        ai_summary=g.ai_summary,
        triaged_by=g.triaged_by,
    )


# ---------- customer ----------


async def _order_context(db: AsyncSession, user: User, order_id: int) -> dict:
    """Facts about the customer's order that the triage model may rely on."""
    order = await order_service.get_order_for_user(db, user, order_id)  # 404 if not theirs
    returns = (
        await db.execute(
            select(ReturnRequest).join(OrderItem, OrderItem.id == ReturnRequest.order_item_id).where(OrderItem.order_id == order.id)
        )
    ).scalars().all()
    return {
        "order_id": order.id,
        "status": order.status.value,
        "payment": f"{order.payment_method.value}, {order.payment_status.value}",
        "total_inr": str(order.grand_total),
        "placed_at": order.created_at,
        "delivered_at": order.delivered_at,
        "seller": order.seller.business_name,
        "items": [f"{i.title} x{i.quantity}" for i in order.items],
        "timeline": [{"status": e.status.value, "at": e.created_at, "note": e.note} for e in order.events],
        "returns": [{"reason": r.reason.value, "status": r.status.value, "refund_inr": str(r.refund_amount)} for r in returns],
    }


async def _load(db: AsyncSession, grievance_id: int) -> Grievance:
    stmt = select(Grievance).where(Grievance.id == grievance_id).options(selectinload(Grievance.events))
    grievance = (await db.execute(stmt.execution_options(populate_existing=True))).scalar_one_or_none()
    if grievance is None:
        raise NotFoundError(f"Complaint {grievance_id} not found")
    return grievance


async def create_grievance(
    db: AsyncSession, user: User, models: AssistantModels | None, data: GrievanceCreate
) -> Grievance:
    context = await _order_context(db, user, data.order_id) if data.order_id else None
    result = await triage(models, data.subject.strip(), data.description.strip(), context, data.language)
    decision = result.decision
    now = utcnow()

    grievance = Grievance(
        user_id=user.id,
        order_id=data.order_id,
        subject=data.subject.strip(),
        description=data.description.strip(),
        language=data.language,
        category=decision.category,
        priority=decision.priority,
        status=GrievanceStatus.AI_RESOLVED if decision.auto_resolve else GrievanceStatus.OPEN,
        ai_summary=decision.summary,
        ai_reply=decision.reply,
        triaged_by=result.triaged_by,
        created_at=now,
        acknowledged_at=now,  # triage acknowledges instantly
        resolve_by=now + timedelta(days=GRIEVANCE_RESOLVE_DAYS),
    )
    grievance.events = [
        GrievanceEvent(status=GrievanceStatus.OPEN, actor=GrievanceActor.CUSTOMER, actor_user_id=user.id, note="Complaint raised.", created_at=now),
        GrievanceEvent(
            status=grievance.status,
            actor=GrievanceActor.AI,
            note=decision.reply
            if decision.auto_resolve
            else f"Acknowledged and sent to the grievance team ({decision.priority.value} priority).",
            created_at=now,
        ),
    ]
    db.add(grievance)
    await db.commit()
    return await _load(db, grievance.id)


async def list_mine(db: AsyncSession, user: User) -> list[Grievance]:
    stmt = (
        select(Grievance)
        .where(Grievance.user_id == user.id)
        .options(selectinload(Grievance.events))
        .order_by(Grievance.id.desc())
    )
    return list((await db.execute(stmt)).scalars().all())


async def get_for_user(db: AsyncSession, user: User, grievance_id: int) -> Grievance:
    grievance = await _load(db, grievance_id)
    if grievance.user_id != user.id and user.role != UserRole.ADMIN:
        raise NotFoundError(f"Complaint {grievance_id} not found")
    return grievance


async def add_customer_comment(db: AsyncSession, user: User, grievance_id: int, message: str) -> Grievance:
    grievance = await get_for_user(db, user, grievance_id)
    if grievance.status not in OPEN_STATES:
        raise ConflictError("This complaint is closed. Reopen it to add more details.")
    db.add(GrievanceEvent(grievance_id=grievance.id, status=grievance.status, actor=GrievanceActor.CUSTOMER, actor_user_id=user.id, note=message.strip()))
    await db.commit()
    return await _load(db, grievance.id)


async def reopen(db: AsyncSession, user: User, grievance_id: int, message: str) -> Grievance:
    """'This didn't help': send an AI-answered (or closed) complaint to a person."""
    grievance = await get_for_user(db, user, grievance_id)
    if not _can_reopen(grievance):
        raise ConflictError("This complaint can't be reopened. Please raise a new one.")
    grievance.status = GrievanceStatus.OPEN
    grievance.resolved_at = None
    grievance.resolve_by = max(grievance.resolve_by, utcnow() + timedelta(days=GRIEVANCE_RESOLVE_DAYS))
    db.add(
        GrievanceEvent(
            grievance_id=grievance.id,
            status=GrievanceStatus.OPEN,
            actor=GrievanceActor.CUSTOMER,
            actor_user_id=user.id,
            note=f"Reopened: {message.strip()}",
        )
    )
    await db.commit()
    return await _load(db, grievance.id)


# ---------- team / admin ----------


async def list_for_admin(
    db: AsyncSession, status: GrievanceStatus | None, open_only: bool
) -> list[tuple[Grievance, User]]:
    stmt = select(Grievance, User).join(User, User.id == Grievance.user_id).options(selectinload(Grievance.events))
    if status is not None:
        stmt = stmt.where(Grievance.status == status)
    elif open_only:
        stmt = stmt.where(Grievance.status.in_(OPEN_STATES))
    stmt = stmt.order_by(PRIORITY_RANK, Grievance.resolve_by, Grievance.id)
    return [(g, u) for g, u in (await db.execute(stmt)).all()]


async def admin_update(db: AsyncSession, admin: User, grievance_id: int, data: GrievanceAdminUpdate) -> tuple[Grievance, User]:
    grievance = await _load(db, grievance_id)
    if grievance.status == GrievanceStatus.RESOLVED:
        raise ConflictError("This complaint is already resolved")
    grievance.status = GrievanceStatus(data.status)
    grievance.resolved_at = utcnow() if grievance.status == GrievanceStatus.RESOLVED else None
    db.add(GrievanceEvent(grievance_id=grievance.id, status=grievance.status, actor=GrievanceActor.ADMIN, actor_user_id=admin.id, note=data.note.strip()))
    await db.commit()
    grievance = await _load(db, grievance.id)
    customer = await db.get(User, grievance.user_id)
    assert customer is not None
    return grievance, customer


async def overview(db: AsyncSession) -> dict:
    now = utcnow()
    open_filter = Grievance.status.in_(OPEN_STATES)
    counts = (
        await db.execute(
            select(
                func.count().filter(open_filter),
                func.count().filter(open_filter, Grievance.priority.in_([GrievancePriority.URGENT, GrievancePriority.HIGH])),
                func.count().filter(open_filter, Grievance.resolve_by < now),
            ).select_from(Grievance)
        )
    ).one()
    flagged = (await db.execute(select(func.count(Review.id)).where(Review.status == ReviewStatus.FLAGGED))).scalar_one()
    pending_returns = (
        await db.execute(select(func.count(ReturnRequest.id)).where(ReturnRequest.status == ReturnStatus.REQUESTED))
    ).scalar_one()
    since = now - timedelta(hours=24)
    orders_today, revenue = (
        await db.execute(
            select(func.count(Order.id), func.coalesce(func.sum(Order.grand_total), 0)).where(
                Order.created_at >= since, Order.status != OrderStatus.CANCELLED
            )
        )
    ).one()
    return {
        "open_grievances": counts[0],
        "urgent_or_high": counts[1],
        "overdue_grievances": counts[2],
        "flagged_reviews": flagged,
        "pending_returns": pending_returns,
        "orders_today": orders_today,
        "revenue_today": str(Decimal(revenue).quantize(Decimal("0.01"))),
    }
