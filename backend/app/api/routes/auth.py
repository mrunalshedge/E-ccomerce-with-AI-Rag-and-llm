from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from app.api.deps import CurrentUser, DbSession
from app.core.rate_limit import rate_limit
from app.core.security import create_access_token
from app.schemas.user import Token, UserCreate, UserRead, UserUpdate
from app.services import user_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit("register", limit=5, window_seconds=600))],
)
async def register(data: UserCreate, db: DbSession) -> UserRead:
    """Register as a customer or seller. Admin accounts are created with the seed script."""
    user = await user_service.create_user(db, data)
    return UserRead.model_validate(user)


@router.post("/login", response_model=Token, dependencies=[Depends(rate_limit("login", limit=10, window_seconds=60))])
async def login(form: Annotated[OAuth2PasswordRequestForm, Depends()], db: DbSession) -> Token:
    """OAuth2 password flow. Put the email in the ``username`` field."""
    user = await user_service.authenticate_user(db, form.username, form.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return Token(access_token=create_access_token(subject=str(user.id), role=user.role.value))


@router.get("/me", response_model=UserRead)
async def me(user: CurrentUser) -> UserRead:
    return UserRead.model_validate(user)


@router.patch("/me", response_model=UserRead)
async def update_me(data: UserUpdate, user: CurrentUser, db: DbSession) -> UserRead:
    """Update your name or preferred language (en / hi / hinglish / mr)."""
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(user, field, value)
    await db.commit()
    return UserRead.model_validate(user)
