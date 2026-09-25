"""Shared FastAPI dependencies: DB session, current user, role checks."""

from collections.abc import Awaitable, Callable
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.user import User, UserRole

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


SellerUser = Annotated[User, Depends(require_role(UserRole.SELLER))]
