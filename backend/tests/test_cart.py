from collections.abc import Awaitable, Callable
from typing import Any

from httpx import AsyncClient

CART = "/api/v1/cart"
Headers = dict[str, str]
MakeHeaders = Callable[..., Awaitable[Headers]]
MakeProduct = Callable[..., Awaitable[dict[str, Any]]]


async def test_new_cart_is_empty_and_items_only_come_from_the_customer(
    client: AsyncClient, register_and_login: MakeHeaders, make_seller: MakeHeaders, make_product: MakeProduct
) -> None:
    await make_product(await make_seller())  # products exist, but nothing is auto-added
    customer = await register_and_login("customer")

    cart = (await client.get(CART, headers=customer)).json()
    assert cart["items"] == []
    assert cart["totals"]["grand_total"] == "0.00"


async def test_add_item_shows_all_inclusive_line_and_totals(
    client: AsyncClient, register_and_login: MakeHeaders, make_seller: MakeHeaders, make_product: MakeProduct
) -> None:
    product = await make_product(await make_seller())
    customer = await register_and_login("customer")

    resp = await client.post(f"{CART}/items", json={"product_id": product["id"], "quantity": 2}, headers=customer)
    assert resp.status_code == 200
    cart = resp.json()
    line = cart["items"][0]
    assert line["quantity"] == 2
    assert line["unit_price"]["final_price"] == "1239.00"
    assert line["line_total"] == "2478.00"
    assert line["seller_name"] == "Pune Handlooms Pvt Ltd"
    totals = cart["totals"]
    assert totals == {
        "items_count": 2,
        "total_base": "2000.00",
        "total_delivery": "80.00",
        "total_platform_fee": "20.00",
        "total_gst": "378.00",
        "grand_total": "2478.00",  # exactly 2 × the price shown on the product page
        "currency": "INR",
    }


async def test_adding_same_product_twice_merges_quantity(
    client: AsyncClient, register_and_login: MakeHeaders, make_seller: MakeHeaders, make_product: MakeProduct
) -> None:
    product = await make_product(await make_seller())
    customer = await register_and_login("customer")
    await client.post(f"{CART}/items", json={"product_id": product["id"], "quantity": 1}, headers=customer)
    resp = await client.post(f"{CART}/items", json={"product_id": product["id"], "quantity": 2}, headers=customer)
    assert len(resp.json()["items"]) == 1
    assert resp.json()["items"][0]["quantity"] == 3


async def test_cannot_add_more_than_stock(
    client: AsyncClient, register_and_login: MakeHeaders, make_seller: MakeHeaders, make_product: MakeProduct
) -> None:
    product = await make_product(await make_seller(), stock=2)
    customer = await register_and_login("customer")
    resp = await client.post(f"{CART}/items", json={"product_id": product["id"], "quantity": 3}, headers=customer)
    assert resp.status_code == 409
    assert "Only 2" in resp.json()["detail"]


async def test_out_of_stock_product(
    client: AsyncClient, register_and_login: MakeHeaders, make_seller: MakeHeaders, make_product: MakeProduct
) -> None:
    product = await make_product(await make_seller(), stock=0)
    customer = await register_and_login("customer")
    resp = await client.post(f"{CART}/items", json={"product_id": product["id"]}, headers=customer)
    assert resp.status_code == 409
    assert "out of stock" in resp.json()["detail"]


async def test_quantity_limits(
    client: AsyncClient, register_and_login: MakeHeaders, make_seller: MakeHeaders, make_product: MakeProduct
) -> None:
    product = await make_product(await make_seller(), stock=50)
    customer = await register_and_login("customer")
    too_many = await client.post(f"{CART}/items", json={"product_id": product["id"], "quantity": 11}, headers=customer)
    assert too_many.status_code == 422
    zero = await client.post(f"{CART}/items", json={"product_id": product["id"], "quantity": 0}, headers=customer)
    assert zero.status_code == 422


async def test_update_and_remove_item(
    client: AsyncClient, register_and_login: MakeHeaders, make_seller: MakeHeaders, make_product: MakeProduct
) -> None:
    product = await make_product(await make_seller())
    customer = await register_and_login("customer")
    await client.post(f"{CART}/items", json={"product_id": product["id"]}, headers=customer)

    updated = await client.patch(f"{CART}/items/{product['id']}", json={"quantity": 4}, headers=customer)
    assert updated.status_code == 200
    assert updated.json()["totals"]["grand_total"] == "4956.00"

    removed = await client.delete(f"{CART}/items/{product['id']}", headers=customer)
    assert removed.status_code == 200
    assert removed.json()["items"] == []

    missing = await client.delete(f"{CART}/items/{product['id']}", headers=customer)
    assert missing.status_code == 404


async def test_unknown_product_is_404(client: AsyncClient, register_and_login: MakeHeaders) -> None:
    customer = await register_and_login("customer")
    resp = await client.post(f"{CART}/items", json={"product_id": 999}, headers=customer)
    assert resp.status_code == 404


async def test_sellers_and_anonymous_users_have_no_cart(client: AsyncClient, make_seller: MakeHeaders) -> None:
    assert (await client.get(CART)).status_code == 401
    assert (await client.get(CART, headers=await make_seller())).status_code == 403
