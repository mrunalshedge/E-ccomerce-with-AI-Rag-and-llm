"""Startup schema bootstrap. Temporary until Alembic migrations are introduced (Phase 2)."""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

import app.models  # noqa: F401  (registers every model on Base.metadata)
from app.db.base import Base


async def init_db(engine: AsyncEngine) -> None:
    """Enable pgvector and create any missing tables."""
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all)
