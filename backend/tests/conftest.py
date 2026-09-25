"""Test fixtures.

Pure unit tests (pricing, security) need nothing. API tests need the Postgres test database
(``POSTGRES_TEST_DB``); they are skipped with a clear message if it isn't reachable.
The schema is rebuilt once per run, and every table is emptied before each test.
"""

import os
from collections.abc import AsyncIterator, Awaitable, Callable
from pathlib import Path
from typing import Any

# Fast password hashing for tests (must be set before settings are first loaded).
os.environ["BCRYPT_ROUNDS"] = "4"
# Without a backend/.env, fall back to throwaway test-only values so the app can be imported.
if not (Path(__file__).resolve().parents[1] / ".env").exists():
    os.environ.setdefault("POSTGRES_USER", "shopsense")
    os.environ.setdefault("POSTGRES_PASSWORD", "shopsense")
    os.environ.setdefault("JWT_SECRET_KEY", "test-only-secret-key-not-for-production-0123456789")

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

import app.models  # noqa: F401  (register models)
from app.core.config import get_settings
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.user import UserRole
from app.schemas.user import UserCreate
from app.services.user_service import create_user
from tests.data import ADDRESS, PRODUCT, SELLER_PROFILE

PASSWORD = "s3cure-pass!"
AuthHeaders = dict[str, str]

@pytest_asyncio.fixture(scope="session")
async def _test_engine() -> AsyncIterator[AsyncEngine]:
    """One pooled engine for the whole run (a new TLS connection to a cloud DB costs ~0.5 s)."""
    engine = create_async_engine(get_settings().test_database_url, pool_size=5)
    try:
        async with engine.begin() as conn:
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
    except (OSError, SQLAlchemyError) as exc:
        await engine.dispose()
        pytest.skip(f"Test database unavailable ({type(exc).__name__}). Check backend/.env.")
    yield engine
    await engine.dispose()


@pytest.fixture
async def db_engine(_test_engine: AsyncEngine) -> AsyncEngine:
    """The shared engine, with every table emptied so each test starts clean."""
    tables = ", ".join(t.name for t in Base.metadata.sorted_tables)
    async with _test_engine.begin() as conn:
        await conn.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))
    return _test_engine


@pytest.fixture
def session_factory(db_engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """For tests that need to change the DB directly (e.g. simulate time passing)."""
    return async_sessionmaker(db_engine, expire_on_commit=False)


@pytest.fixture
async def client(session_factory: async_sessionmaker[AsyncSession]) -> AsyncIterator[AsyncClient]:
    async def override_get_db() -> AsyncIterator[AsyncSession]:
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    # ASGITransport doesn't run the lifespan, so the app never touches the dev database.
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


async def _login(client: AsyncClient, email: str) -> AuthHeaders:
    resp = await client.post("/api/v1/auth/login", data={"username": email, "password": PASSWORD})
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


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
        return await _login(client, email)

    return _make


@pytest.fixture
def make_seller(
    client: AsyncClient, register_and_login: Callable[..., Awaitable[AuthHeaders]]
) -> Callable[..., Awaitable[AuthHeaders]]:
    """A seller account with a seller profile; returns its auth headers."""

    async def _make(email: str = "seller@example.com", business_name: str = "Pune Handlooms Pvt Ltd") -> AuthHeaders:
        headers = await register_and_login("seller", email)
        profile = {**SELLER_PROFILE, "business_name": business_name}
        resp = await client.post("/api/v1/sellers/me", json=profile, headers=headers)
        assert resp.status_code == 201, resp.text
        return headers

    return _make


@pytest.fixture
def make_product(client: AsyncClient) -> Callable[..., Awaitable[dict[str, Any]]]:
    async def _make(seller_headers: AuthHeaders, **overrides: Any) -> dict[str, Any]:
        resp = await client.post("/api/v1/products", json={**PRODUCT, **overrides}, headers=seller_headers)
        assert resp.status_code == 201, resp.text
        return resp.json()

    return _make


@pytest.fixture
def place_order(client: AsyncClient) -> Callable[..., Awaitable[dict[str, Any]]]:
    """Add products to the cart and check out; returns the checkout response."""

    async def _place(
        customer: AuthHeaders, items: list[tuple[int, int]], payment_method: str = "upi"
    ) -> dict[str, Any]:
        for product_id, quantity in items:
            resp = await client.post(
                "/api/v1/cart/items", json={"product_id": product_id, "quantity": quantity}, headers=customer
            )
            assert resp.status_code == 200, resp.text
        total = (await client.get("/api/v1/cart", headers=customer)).json()["totals"]["grand_total"]
        resp = await client.post(
            "/api/v1/orders",
            json={"payment_method": payment_method, "shipping_address": ADDRESS, "expected_total": total},
            headers=customer,
        )
        assert resp.status_code == 201, resp.text
        return resp.json()

    return _place


@pytest.fixture
async def admin_headers(client: AsyncClient, session_factory: async_sessionmaker[AsyncSession]) -> AuthHeaders:
    """Admins can't self-register, so create one directly (as the seed script does)."""
    async with session_factory() as db:
        data = UserCreate(name="Admin", email="admin@example.com", password=PASSWORD)
        await create_user(db, data, role=UserRole.ADMIN)
    return await _login(client, "admin@example.com")
