from collections.abc import Awaitable, Callable
from decimal import Decimal
from typing import Any

from httpx import AsyncClient
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.product import Product
from tests.data import ADDRESS

ORDERS = "/api/v1/orders"
Headers = dict[str, str]
MakeHeaders = Callable[..., Awaitable[Headers]]
MakeProduct = Callable[..., Awaitable[dict[str, Any]]]
PlaceOrder = Callable[..., Awaitable[dict[str, Any]]]
Sessions = async_sessionmaker[AsyncSession]


async def _stock(client: AsyncClient, product_id: int) -> int:
    return (await client.get(f"/api/v1/products/{product_id}")).json()["stock"]


async def _add(client: AsyncClient, customer: Headers, product_id: int, quantity: int = 1) -> None:
    resp = await client.post("/api/v1/cart/items", json={"product_id": product_id, "quantity": quantity}, headers=customer)
    assert resp.status_code == 200, resp.text


def _checkout_body(total: str, payment_method: str = "upi") -> dict[str, str]:
    return {"payment_method": payment_method, "shipping_address": ADDRESS, "expected_total": total}


async def test_checkout_splits_by_seller_snapshots_prices_and_updates_stock(
    client: AsyncClient,
    register_and_login: MakeHeaders,
    make_seller: MakeHeaders,
    make_product: MakeProduct,
    place_order: PlaceOrder,
) -> None:
    kurta = await make_product(await make_seller())
    saree = await make_product(
        await make_seller("seller2@example.com", "Kanchi Silks"), title="Silk Saree", base_price="5000", stock=3
    )
    customer = await register_and_login("customer")

    result = await place_order(customer, [(kurta["id"], 2), (saree["id"], 1)])

    assert len(result["orders"]) == 2
    kurta_order, saree_order = result["orders"]
    assert kurta_order["seller"]["business_name"] == "Pune Handlooms Pvt Ltd"
    assert kurta_order["totals"]["grand_total"] == "2478.00"
    assert kurta_order["items"][0]["unit_price"]["final_price"] == "1239.00"
    assert kurta_order["payment_method"] == "upi"
    assert kurta_order["payment_status"] == "paid"
    assert kurta_order["status"] == "placed"
    assert kurta_order["timeline"][0]["status"] == "placed"
    assert saree_order["seller"]["business_name"] == "Kanchi Silks"
    assert Decimal(result["grand_total"]) == Decimal("2478.00") + Decimal(saree_order["totals"]["grand_total"])

    assert await _stock(client, kurta["id"]) == 3
    assert await _stock(client, saree["id"]) == 2
    assert (await client.get("/api/v1/cart", headers=customer)).json()["items"] == []
    assert len((await client.get(ORDERS, headers=customer)).json()) == 2


async def test_payment_method_must_be_chosen_explicitly(
    client: AsyncClient, register_and_login: MakeHeaders, make_seller: MakeHeaders, make_product: MakeProduct
) -> None:
    product = await make_product(await make_seller())
    customer = await register_and_login("customer")
    await _add(client, customer, product["id"])

    resp = await client.post(ORDERS, json={"shipping_address": ADDRESS, "expected_total": "1239.00"}, headers=customer)
    assert resp.status_code == 422  # no silent default (e.g. COD)


async def test_cod_order_is_pending_until_delivered(
    client: AsyncClient, register_and_login: MakeHeaders, make_seller: MakeHeaders, make_product: MakeProduct,
    place_order: PlaceOrder,
) -> None:
    seller = await make_seller()
    product = await make_product(seller)
    customer = await register_and_login("customer")
    order = (await place_order(customer, [(product["id"], 1)], payment_method="cod"))["orders"][0]
    assert order["payment_method"] == "cod"
    assert order["payment_status"] == "pending"

    status_url = f"/api/v1/sellers/me/orders/{order['id']}/status"
    await client.patch(status_url, json={"status": "shipped"}, headers=seller)
    delivered = await client.patch(status_url, json={"status": "delivered"}, headers=seller)
    assert delivered.status_code == 200
    body = delivered.json()
    assert body["payment_status"] == "paid"
    assert body["delivered_at"] is not None
    assert [e["status"] for e in body["timeline"]] == ["placed", "shipped", "delivered"]


async def test_checkout_refuses_a_total_the_customer_did_not_see(
    client: AsyncClient, register_and_login: MakeHeaders, make_seller: MakeHeaders, make_product: MakeProduct
) -> None:
    product = await make_product(await make_seller())
    customer = await register_and_login("customer")
    await _add(client, customer, product["id"])

    resp = await client.post(ORDERS, json=_checkout_body("1000.00"), headers=customer)
    assert resp.status_code == 409
    assert "₹1239.00" in resp.json()["detail"]
    assert len((await client.get("/api/v1/cart", headers=customer)).json()["items"]) == 1  # cart untouched
    assert await _stock(client, product["id"]) == 5


async def test_price_change_after_adding_to_cart_is_caught(
    client: AsyncClient,
    register_and_login: MakeHeaders,
    make_seller: MakeHeaders,
    make_product: MakeProduct,
    session_factory: Sessions,
) -> None:
    product = await make_product(await make_seller())
    customer = await register_and_login("customer")
    await _add(client, customer, product["id"])
    seen_total = (await client.get("/api/v1/cart", headers=customer)).json()["totals"]["grand_total"]

    async with session_factory() as db:  # seller raises the price behind the scenes
        await db.execute(update(Product).where(Product.id == product["id"]).values(base_price=Decimal("1100")))
        await db.commit()

    resp = await client.post(ORDERS, json=_checkout_body(seen_total), headers=customer)
    assert resp.status_code == 409
    assert "Please review your cart" in resp.json()["detail"]


async def test_stock_sold_out_between_cart_and_checkout(
    client: AsyncClient,
    register_and_login: MakeHeaders,
    make_seller: MakeHeaders,
    make_product: MakeProduct,
    session_factory: Sessions,
) -> None:
    product = await make_product(await make_seller())
    customer = await register_and_login("customer")
    await _add(client, customer, product["id"], 3)

    async with session_factory() as db:
        await db.execute(update(Product).where(Product.id == product["id"]).values(stock=1))
        await db.commit()

    resp = await client.post(ORDERS, json=_checkout_body("3717.00"), headers=customer)
    assert resp.status_code == 409
    assert "only 1 left" in resp.json()["detail"]


async def test_empty_cart_checkout(client: AsyncClient, register_and_login: MakeHeaders) -> None:
    customer = await register_and_login("customer")
    resp = await client.post(ORDERS, json=_checkout_body("0.00"), headers=customer)
    assert resp.status_code == 400


async def test_cancel_before_shipping_refunds_and_restocks(
    client: AsyncClient, register_and_login: MakeHeaders, make_seller: MakeHeaders, make_product: MakeProduct,
    place_order: PlaceOrder,
) -> None:
    product = await make_product(await make_seller())
    customer = await register_and_login("customer")
    order = (await place_order(customer, [(product["id"], 2)]))["orders"][0]
    assert await _stock(client, product["id"]) == 3

    resp = await client.post(f"{ORDERS}/{order['id']}/cancel", headers=customer)
    assert resp.status_code == 200
    assert resp.json()["status"] == "cancelled"
    assert resp.json()["payment_status"] == "refunded"
    assert await _stock(client, product["id"]) == 5

    again = await client.post(f"{ORDERS}/{order['id']}/cancel", headers=customer)
    assert again.status_code == 409


async def test_cancelled_cod_order_is_void_not_refunded(
    client: AsyncClient, register_and_login: MakeHeaders, make_seller: MakeHeaders, make_product: MakeProduct,
    place_order: PlaceOrder,
) -> None:
    product = await make_product(await make_seller())
    customer = await register_and_login("customer")
    order = (await place_order(customer, [(product["id"], 1)], payment_method="cod"))["orders"][0]
    resp = await client.post(f"{ORDERS}/{order['id']}/cancel", headers=customer)
    assert resp.json()["payment_status"] == "void"


async def test_cannot_cancel_after_shipping(
    client: AsyncClient, register_and_login: MakeHeaders, make_seller: MakeHeaders, make_product: MakeProduct,
    place_order: PlaceOrder,
) -> None:
    seller = await make_seller()
    product = await make_product(seller)
    customer = await register_and_login("customer")
    order = (await place_order(customer, [(product["id"], 1)]))["orders"][0]
    await client.patch(f"/api/v1/sellers/me/orders/{order['id']}/status", json={"status": "shipped"}, headers=seller)

    resp = await client.post(f"{ORDERS}/{order['id']}/cancel", headers=customer)
    assert resp.status_code == 409
    assert "already shipped" in resp.json()["detail"]


async def test_seller_status_rules(
    client: AsyncClient, register_and_login: MakeHeaders, make_seller: MakeHeaders, make_product: MakeProduct,
    place_order: PlaceOrder,
) -> None:
    seller = await make_seller()
    other_seller = await make_seller("seller2@example.com", "Kanchi Silks")
    product = await make_product(seller)
    customer = await register_and_login("customer")
    order = (await place_order(customer, [(product["id"], 1)]))["orders"][0]
    url = f"/api/v1/sellers/me/orders/{order['id']}/status"

    skip = await client.patch(url, json={"status": "delivered"}, headers=seller)
    assert skip.status_code == 409  # can't jump from placed to delivered
    not_theirs = await client.patch(url, json={"status": "shipped"}, headers=other_seller)
    assert not_theirs.status_code == 404
    by_customer = await client.patch(url, json={"status": "shipped"}, headers=customer)
    assert by_customer.status_code == 403

    listed = (await client.get("/api/v1/sellers/me/orders", headers=seller)).json()
    assert [o["id"] for o in listed] == [order["id"]]
    assert (await client.get("/api/v1/sellers/me/orders", headers=other_seller)).json() == []


async def test_order_visibility(
    client: AsyncClient, register_and_login: MakeHeaders, make_seller: MakeHeaders, make_product: MakeProduct,
    place_order: PlaceOrder, admin_headers: Headers,
) -> None:
    seller = await make_seller()
    product = await make_product(seller)
    customer = await register_and_login("customer")
    stranger = await register_and_login("customer", "stranger@example.com")
    order = (await place_order(customer, [(product["id"], 1)]))["orders"][0]
    url = f"{ORDERS}/{order['id']}"

    assert (await client.get(url, headers=customer)).status_code == 200
    assert (await client.get(url, headers=seller)).status_code == 200
    assert (await client.get(url, headers=admin_headers)).status_code == 200
    assert (await client.get(url, headers=stranger)).status_code == 404
