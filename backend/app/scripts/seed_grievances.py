"""Demo admin account and a few complaints (triaged by Gemini if configured, else by keywords).
Idempotent: skipped when the same buyer already raised the same subject. Called from seed_demo."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.llm import get_assistant_models
from app.models.grievance import Grievance
from app.models.order import Order
from app.models.user import UserRole
from app.schemas.grievance import GrievanceCreate
from app.schemas.user import UserCreate
from app.services import grievance_service, user_service

ADMIN_EMAIL = "admin@shopsense.dev"

# (buyer email, subject, description, language, attach the buyer's first order?)
COMPLAINTS = [
    ("priya.sharma@shopsense.dev", "Button came loose on my kurta",
     "One button on the kurta was hanging loose when it arrived. I'd like a replacement or partial refund.", "en", True),
    ("rahul.verma@shopsense.dev", "Paise do baar kat gaye",
     "Earbuds ke order ke liye mere account se do baar payment kat gaya. Ek refund chahiye.", "en", True),
    ("kavya.iyer@shopsense.dev", "रिटर्न कितने दिन में कर सकते हैं?",
     "अगर साड़ी पसंद न आए तो कितने दिनों में वापस कर सकती हूँ?", "hi", False),
]


async def seed_admin(db: AsyncSession, password: str) -> bool:
    if await user_service.get_user_by_email(db, ADMIN_EMAIL):
        return False
    await user_service.create_user(
        db, UserCreate(name="ShopSense Admin", email=ADMIN_EMAIL, password=password), role=UserRole.ADMIN
    )
    return True


async def seed_grievances(db: AsyncSession) -> int:
    models = get_assistant_models()
    created = 0
    for email, subject, description, language, with_order in COMPLAINTS:
        user = await user_service.get_user_by_email(db, email)
        if user is None:
            continue
        exists = await db.execute(select(Grievance.id).where(Grievance.user_id == user.id, Grievance.subject == subject))
        if exists.first() is not None:
            continue
        order_id = None
        if with_order:
            order_id = (await db.execute(select(Order.id).where(Order.user_id == user.id).order_by(Order.id))).scalars().first()
        await grievance_service.create_grievance(
            db, user, models, GrievanceCreate(order_id=order_id, subject=subject, description=description, language=language)
        )
        created += 1
    return created
