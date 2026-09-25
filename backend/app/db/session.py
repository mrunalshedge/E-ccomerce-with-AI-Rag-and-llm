"""Async engine, session factory and the ``get_db`` FastAPI dependency."""

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings

_settings = get_settings()

engine = create_async_engine(_settings.database_url, echo=_settings.sql_echo, pool_pre_ping=True)

# expire_on_commit=False: objects stay usable after commit without an implicit (sync) reload,
# which would fail under asyncio.
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def get_db() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session
