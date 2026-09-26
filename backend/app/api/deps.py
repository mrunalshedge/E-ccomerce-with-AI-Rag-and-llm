"""Shared FastAPI dependencies: DB session, current user, role checks."""

from collections.abc import Awaitable, Callable
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import PermissionDeniedError
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.seller import Seller
from app.models.user import User, UserRole
from app.services import seller_service

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{get_settings().api_v1_prefix}/auth/login")

DbSession = Annotated[AsyncSession, Depends(get_db)]


async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)], db: DbSession) -> User:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        user_id = int(decode_access_token(token)["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        raise credentials_error from None

    user = await db.get(User, user_id)
    if user is None:  # token for a deleted user
        raise credentials_error
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]

_optional_oauth2 = OAuth2PasswordBearer(tokenUrl=f"{get_settings().api_v1_prefix}/auth/login", auto_error=False)


async def get_optional_user(token: Annotated[str | None, Depends(_optional_oauth2)], db: DbSession) -> User | None:
    """The logged-in user if a valid token was sent, otherwise ``None`` (for public endpoints that
    do more for logged-in users). An invalid token is treated like no token."""
    if not token:
        return None
    try:
        user_id = int(decode_access_token(token)["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        return None
    return await db.get(User, user_id)


OptionalUser = Annotated[User | None, Depends(get_optional_user)]


def require_role(*roles: UserRole | str) -> Callable[[User], Awaitable[User]]:
    """Dependency factory: ``Depends(require_role("seller"))`` allows only those roles.

    The role is read from the database (via ``get_current_user``), not trusted from the JWT.
    """
    allowed = {UserRole(r) for r in roles}

    async def checker(user: CurrentUser) -> User:
        if user.role not in allowed:
            needed = " or ".join(sorted(r.value for r in allowed))
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail=f"This action requires the {needed} role")
        return user

    return checker


CustomerUser = Annotated[User, Depends(require_role(UserRole.CUSTOMER))]
SellerUser = Annotated[User, Depends(require_role(UserRole.SELLER))]
AdminUser = Annotated[User, Depends(require_role(UserRole.ADMIN))]


async def get_current_seller(user: SellerUser, db: DbSession) -> Seller:
    """The logged-in seller's profile; sellers must create one before selling."""
    seller = await seller_service.get_seller_by_user_id(db, user.id)
    if seller is None:
        raise PermissionDeniedError("Create your seller profile (POST /api/v1/sellers/me) first")
    return seller


CurrentSeller = Annotated[Seller, Depends(get_current_seller)]
