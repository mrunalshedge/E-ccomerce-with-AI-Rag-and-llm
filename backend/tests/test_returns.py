from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta
from typing import Any

from httpx import AsyncClient
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.order import Order

RETURNS = "/api/v1/returns"
Headers = dict[str, str]
MakeHeaders = Callable[..., Awaitable[Headers]]
MakeProduct = Callable[..., Awaitable[dict[str, Any]]]
PlaceOrder = Callable[..., Awaitable[dict[str, Any]]]


async def _delivered_order(
    client: AsyncClient,
    seller: Headers,
    customer: Headers,
    make_product: MakeProduct,
    place_order: PlaceOrder,
    **product_overrides: Any,
) -> dict[str, Any]:
    product = await make_product(seller, **product_overrides)
    order = (await place_order(customer, [(product["id"], 1)]))["orders"][0]
    url = f"/api/v1/sellers/me/orders/{order['id']}/status"
    await client.patch(url, json={"status": "shipped"}, headers=seller)
    resp = await client.patch(url, json={"status": "delivered"}, headers=seller)
    assert resp.status_code == 200, resp.text
    return resp.json()


def _return_body(order: dict[str, Any], reason: str) -> dict[str, Any]:
    return {"order_item_id": order["items"][0]["id"], "reason": reason, "description": "Received a different product"}


async def _trust_score(client: AsyncClient, seller: Headers) -> float:
    return (await client.get("/api/v1/sellers/me", headers=seller)).json()["trust_score"]


async def test_wrong_or_fake_items_are_returnable_even_when_product_is_not(
    client: AsyncClient, register_and_login: MakeHeaders, make_seller: MakeHeaders, make_product: MakeProduct,
    place_order: PlaceOrder,
) -> None:
    seller = await make_seller()
    customer = await register_and_login("customer")
    order = await _delivered_order(client, seller, customer, make_product, place_order, is_returnable=False)

    damaged = await client.post(RETURNS, json=_return_body(order, "damaged"), headers=customer)
    assert damaged.status_code == 409
    assert "non-returnable" in damaged.json()["detail"]

    wrong = await client.post(RETURNS, json=_return_body(order, "wrong_item"), headers=customer)
    assert wrong.status_code == 201
    body = wrong.json()
    assert body["status"] == "requested"
    assert body["refund_amount"] == "1239.00"
    assert body["product_title"] == "Cotton Kurta"

    duplicate = await client.post(RETURNS, json=_return_body(order, "counterfeit"), headers=customer)
    assert duplicate.status_code == 409


async def test_return_needs_delivery_first(
    client: AsyncClient, register_and_login: MakeHeaders, make_seller: MakeHeaders, make_product: MakeProduct,
    place_order: PlaceOrder,
) -> None:
    product = await make_product(await make_seller())
    customer = await register_and_login("customer")
    order = (await place_order(customer, [(product["id"], 1)]))["orders"][0]
    resp = await client.post(RETURNS, json=_return_body(order, "wrong_item"), headers=customer)
    assert resp.status_code == 409
    assert "delivered" in resp.json()["detail"]


async def test_return_window_closes_after_7_days(
    client: AsyncClient, register_and_login: MakeHeaders, make_seller: MakeHeaders, make_product: MakeProduct,
    place_order: PlaceOrder, session_factory: async_sessionmaker[AsyncSession],
) -> None:
    seller = await make_seller()
    customer = await register_and_login("customer")
    order = await _delivered_order(client, seller, customer, make_product, place_order)

    async with session_factory() as db:  # simulate 8 days passing
        eight_days_ago = datetime.now(UTC) - timedelta(days=8)
        await db.execute(update(Order).where(Order.id == order["id"]).values(delivered_at=eight_days_ago))
        await db.commit()

    resp = await client.post(RETURNS, json=_return_body(order, "counterfeit"), headers=customer)
    assert resp.status_code == 409
    assert "return window closed" in resp.json()["detail"]


async def test_cannot_return_someone_elses_item(
    client: AsyncClient, register_and_login: MakeHeaders, make_seller: MakeHeaders, make_product: MakeProduct,
    place_order: PlaceOrder,
) -> None:
    seller = await make_seller()
    customer = await register_and_login("customer")
    stranger = await register_and_login("customer", "stranger@example.com")
    order = await _delivered_order(client, seller, customer, make_product, place_order)
    resp = await client.post(RETURNS, json=_return_body(order, "wrong_item"), headers=stranger)
    assert resp.status_code == 404


async def test_approved_counterfeit_return_lowers_seller_trust(
    client: AsyncClient, register_and_login: MakeHeaders, make_seller: MakeHeaders, make_product: MakeProduct,
    place_order: PlaceOrder, admin_headers: Headers,
) -> None:
    seller = await make_seller()
    customer = await register_and_login("customer")
    order = await _delivered_order(client, seller, customer, make_product, place_order)
    ret = (await client.post(RETURNS, json=_return_body(order, "counterfeit"), headers=customer)).json()

    # Seller can see returns against their items; customer sees their own.
    assert [r["id"] for r in (await client.get("/api/v1/sellers/me/returns", headers=seller)).json()] == [ret["id"]]
    assert [r["id"] for r in (await client.get(RETURNS, headers=customer)).json()] == [ret["id"]]
    pending = await client.get("/api/v1/admin/returns", params={"status": "requested"}, headers=admin_headers)
    assert [r["id"] for r in pending.json()] == [ret["id"]]

    url = f"/api/v1/admin/returns/{ret['id']}/resolve"
    by_customer = await client.post(url, json={"decision": "approve", "note": "ok"}, headers=customer)
    assert by_customer.status_code == 403

    approved = await client.post(url, json={"decision": "approve", "note": "Verified fake"}, headers=admin_headers)
    assert approved.status_code == 200
    assert approved.json()["status"] == "approved"
    assert approved.json()["resolved_at"] is not None
    assert await _trust_score(client, seller) == 95.0

    twice = await client.post(url, json={"decision": "reject", "note": "changed mind"}, headers=admin_headers)
    assert twice.status_code == 409


async def test_damaged_or_rejected_returns_do_not_affect_trust(
    client: AsyncClient, register_and_login: MakeHeaders, make_seller: MakeHeaders, make_product: MakeProduct,
    place_order: PlaceOrder, admin_headers: Headers,
) -> None:
    seller = await make_seller()
    customer = await register_and_login("customer")
    first = await _delivered_order(client, seller, customer, make_product, place_order)
    second = await _delivered_order(client, seller, customer, make_product, place_order, title="Linen Shirt")

    damaged = (await client.post(RETURNS, json=_return_body(first, "damaged"), headers=customer)).json()
    wrong = (await client.post(RETURNS, json=_return_body(second, "wrong_item"), headers=customer)).json()

    resolve = "/api/v1/admin/returns/{}/resolve"
    await client.post(resolve.format(damaged["id"]), json={"decision": "approve", "note": "Courier damage"}, headers=admin_headers)
    rejected = await client.post(
        resolve.format(wrong["id"]), json={"decision": "reject", "note": "Photos show correct item"}, headers=admin_headers
    )
    assert rejected.json()["status"] == "rejected"
    assert await _trust_score(client, seller) == 100.0
