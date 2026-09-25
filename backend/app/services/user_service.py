from functools import lru_cache

from anyio import to_thread
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ConflictError
from app.core.security import hash_password, verify_password
from app.models.user import User, UserRole
from app.schemas.user import UserCreate


@lru_cache
def _dummy_hash() -> str:
    """Hash compared against when the email doesn't exist, so login takes the same time
    either way and doesn't reveal which emails are registered."""
    return hash_password("dummy-password-for-timing")


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(select(User).where(User.email == email.lower()))
    return result.scalar_one_or_none()


async def create_user(db: AsyncSession, data: UserCreate, role: UserRole | None = None) -> User:
    """Create a user. ``role`` overrides ``data.role`` (used by the admin seed script)."""
    if await get_user_by_email(db, data.email) is not None:
        raise ConflictError("Email is already registered")

    # bcrypt is CPU-bound; run it off the event loop.
    hashed = await to_thread.run_sync(hash_password, data.password)
    user = User(
        name=data.name,
        email=data.email.lower(),
        hashed_password=hashed,
        role=role or data.role,
        preferred_language=data.preferred_language,
    )
    db.add(user)
    try:
        await db.commit()
    except IntegrityError as exc:  # concurrent registration with the same email
        await db.rollback()
        raise ConflictError("Email is already registered") from exc
    return user


async def authenticate_user(db: AsyncSession, email: str, password: str) -> User | None:
    user = await get_user_by_email(db, email)
    hashed = user.hashed_password if user else _dummy_hash()
    password_ok = await to_thread.run_sync(verify_password, password, hashed)
    return user if user and password_ok else None
