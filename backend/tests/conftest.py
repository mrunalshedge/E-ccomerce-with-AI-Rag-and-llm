"""Test fixtures.

Pure unit tests (pricing, security) need nothing. API tests need the Postgres test database
(``POSTGRES_TEST_DB``, created by docker-compose); they are skipped with a clear message if
it isn't reachable. Tables are dropped and recreated for every test.
"""

import os
from collections.abc import AsyncIterator, Awaitable, Callable
from pathlib import Path

# Without a backend/.env, fall back to throwaway test-only values so the app can be imported.
if not (Path(__file__).resolve().parents[1] / ".env").exists():
    os.environ.setdefault("POSTGRES_USER", "shopsense")
    os.environ.setdefault("POSTGRES_PASSWORD", "shopsense")
    os.environ.setdefault("JWT_SECRET_KEY", "test-only-secret-key-not-for-production-0123456789")

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

import app.models  # noqa: F401  (register models)
from app.core.config import get_settings
from app.db.base import Base
from app.db.session import get_db
from app.main import app

PASSWORD = "s3cure-pass!"


@pytest.fixture
async def db_engine() -> AsyncIterator[AsyncEngine]:
    engine = create_async_engine(get_settings().test_database_url, poolclass=NullPool)
    try:
        async with engine.begin() as conn:
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
    except (OSError, SQLAlchemyError) as exc:
        await engine.dispose()
        pytest.skip(f"Test database unavailable ({type(exc).__name__}). Run `docker compose up -d`.")
    yield engine
    await engine.dispose()


@pytest.fixture
async def client(db_engine: AsyncEngine) -> AsyncIterator[AsyncClient]:
    sessionmaker = async_sessionmaker(db_engine, expire_on_commit=False)

    async def override_get_db() -> AsyncIterator:
        async with sessionmaker() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    # ASGITransport doesn't run the lifespan, so the app never touches the dev database.
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


AuthHeaders = dict[str, str]


@pytest.fixture
def register_and_login(client: AsyncClient) -> Callable[..., Awaitable[AuthHeaders]]:
    """Register a user with the given role and return bearer-token headers."""

    async def _make(role: str = "customer", email: str | None = None) -> AuthHeaders:
        email = email or f"{role}@example.com"
        resp = await client.post(
            "/api/v1/auth/register",
            json={"name": f"Test {role}", "email": email, "password": PASSWORD, "role": role},
        )
        assert resp.status_code == 201, resp.text
        resp = await client.post("/api/v1/auth/login", data={"username": email, "password": PASSWORD})
        assert resp.status_code == 200, resp.text
        return {"Authorization": f"Bearer {resp.json()['access_token']}"}

    return _make
