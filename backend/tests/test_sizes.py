"""Clothing sizes: per-size stock, size charts, fit feedback, size advice and size exchanges."""

from collections.abc import Awaitable, Callable
from typing import Any

import pytest
from httpx import AsyncClient

from app.services.size_service import fit_summary, recommend_size, to_cm, validate_chart
from tests.data import ADDRESS

Headers = dict[str, str]
MakeHeaders = Callable[..., Awaitable[Headers]]
MakeProduct = Callable[..., Awaitable[dict[str, Any]]]

CART = "/api/v1/cart"
SIZES = [{"size": "S", "stock": 2}, {"size": "M", "stock": 3}, {"size": "L", "stock": 0}]
CHART = [
    {"size": "S", "chest": 96, "length": 104},
    {"size": "M", "chest": 102, "length": 106},
    {"size": "L", "chest": 108, "length": 108},
]


# ---------- pure logic ----------


def test_fit_summary_needs_three_answers_and_a_clear_majority() -> None:
    assert fit_summary({"runs_small": 2}).verdict is None
    assert fit_summary({"runs_small": 2, "true_to_size": 1}).verdict == "runs_small"
    assert fit_summary({"runs_small": 1, "true_to_size": 1, "runs_large": 1}).verdict == "mixed"
    assert fit_summary({"true_to_size": 4, "runs_large": 1}).total == 5


def test_recommend_size_uses_ease_stock_and_buyer_feedback() -> None:
    all_sizes = ["S", "M", "L"]
    # Body chest 94 cm: S (96) leaves only 2 cm, M (102) leaves 8 cm ≥ 6 cm ease.
    assert recommend_size(CHART, all_sizes, {"chest": 94}, None).size == "M"
    # Buyers say it runs small → one size up.
    advice = recommend_size(CHART, all_sizes, {"chest": 94}, "runs_small")
    assert advice.size == "L" and "runs small" in advice.reason
    # Out-of-stock sizes are never suggested.
    assert recommend_size(CHART, ["S", "L"], {"chest": 94}, None).size == "L"
    # Nothing is big enough → the largest, with an honest warning.
    tight = recommend_size(CHART, all_sizes, {"chest": 120}, None)
    assert tight.size == "L" and "tight" in tight.reason
    # No chart / no usable measurement → no guess.
    assert recommend_size(None, all_sizes, {"chest": 94}, None).size is None
    assert recommend_size(CHART, all_sizes, {"length": 100}, None).size is None
    assert to_cm(40, "inch") == 101.6


def test_validate_chart_rejects_unknown_sizes_keys_and_values() -> None:
    validate_chart(CHART, ["S", "M", "L"])
    for bad in ([{"size": "XL", "chest": 100}], [{"size": "S", "colour": 1}], [{"size": "S", "chest": 900}]):
        with pytest.raises(ValueError):
            validate_chart(bad, ["S", "M", "L"])


# ---------- API ----------


async def _sized_product(make_seller: MakeHeaders, make_product: MakeProduct) -> tuple[Headers, dict[str, Any]]:
    seller = await make_seller()
    product = await make_product(seller, sizes=SIZES, size_chart=CHART)
    return seller, product


async def test_sized_product_stock_is_the_sum_of_its_sizes(
    client: AsyncClient, make_seller: MakeHeaders, make_product: MakeProduct
) -> None:
    seller, product = await _sized_product(make_seller, make_product)
    assert product["stock"] == 5
    assert product["sizes"] == SIZES
    assert product["size_chart"][1]["chest"] == 102
    assert product["fit"] == {"runs_small": 0, "true_to_size": 0, "runs_large": 0, "verdict": None}

    assert (await make_seller_post(client, seller, size_chart=CHART)).status_code == 422  # a chart needs sizes
    dupes = [{"size": "M", "stock": 1}, {"size": "m", "stock": 1}]
    assert (await make_seller_post(client, seller, sizes=dupes)).status_code == 422


async def make_seller_post(client: AsyncClient, seller: Headers, **fields: Any) -> Any:
    body = {"title": "Shirt", "description": "Cotton shirt", "category": "clothing", "base_price": "500", **fields}
    return await client.post("/api/v1/products", json=body, headers=seller)


async def test_cart_requires_a_valid_size_and_checks_size_stock(
    client: AsyncClient, register_and_login: MakeHeaders, make_seller: MakeHeaders, make_product: MakeProduct
) -> None:
    _, product = await _sized_product(make_seller, make_product)
    plain = await make_product(await make_seller("plain@example.com", "Plain Store"), title="Mug")
    customer = await register_and_login()
    add = f"{CART}/items"

    no_size = await client.post(add, json={"product_id": product["id"]}, headers=customer)
    assert no_size.status_code == 400 and "choose a size" in no_size.json()["detail"]
    wrong = await client.post(add, json={"product_id": product["id"], "size": "XS"}, headers=customer)
    assert wrong.status_code == 400
    sold_out = await client.post(add, json={"product_id": product["id"], "size": "L"}, headers=customer)
    assert sold_out.status_code == 409
    sized_plain = await client.post(add, json={"product_id": plain["id"], "size": "M"}, headers=customer)
    assert sized_plain.status_code == 400

    # The same product in two sizes = two cart lines, each limited by its own size's stock.
    await client.post(add, json={"product_id": product["id"], "size": "S", "quantity": 2}, headers=customer)
    too_many = await client.post(add, json={"product_id": product["id"], "size": "S"}, headers=customer)
    assert too_many.status_code == 409 and "size S" in too_many.json()["detail"]
    resp = await client.post(add, json={"product_id": product["id"], "size": "M"}, headers=customer)
    lines = {line["size"]: line for line in resp.json()["items"]}
    assert lines["S"]["quantity"] == 2 and lines["S"]["available_stock"] == 2
    assert lines["M"]["quantity"] == 1 and lines["M"]["available_stock"] == 3

    item = f"{add}/{product['id']}"
    updated = await client.patch(item, params={"size": "M"}, json={"quantity": 3}, headers=customer)
    assert {line["size"]: line["quantity"] for line in updated.json()["items"]} == {"S": 2, "M": 3}
    removed = await client.delete(item, params={"size": "S"}, headers=customer)
    assert [line["size"] for line in removed.json()["items"]] == ["M"]


async def test_checkout_and_cancel_move_size_stock(
    client: AsyncClient, register_and_login: MakeHeaders, make_seller: MakeHeaders, make_product: MakeProduct
) -> None:
    _, product = await _sized_product(make_seller, make_product)
    customer = await register_and_login()
    await client.post(f"{CART}/items", json={"product_id": product["id"], "size": "M", "quantity": 2}, headers=customer)
    total = (await client.get(CART, headers=customer)).json()["totals"]["grand_total"]
    body = {"payment_method": "upi", "shipping_address": ADDRESS, "expected_total": total}
    order = (await client.post("/api/v1/orders", json=body, headers=customer)).json()["orders"][0]
    assert order["items"][0]["size"] == "M"

    after = (await client.get(f"/api/v1/products/{product['id']}")).json()
    assert {s["size"]: s["stock"] for s in after["sizes"]} == {"S": 2, "M": 1, "L": 0}
    assert after["stock"] == 3

    await client.post(f"/api/v1/orders/{order['id']}/cancel", headers=customer)
    restocked = (await client.get(f"/api/v1/products/{product['id']}")).json()
    assert {s["size"]: s["stock"] for s in restocked["sizes"]} == {"S": 2, "M": 3, "L": 0}
    assert restocked["stock"] == 5


async def test_seller_edits_sizes_and_total_stock_follows(
    client: AsyncClient, make_seller: MakeHeaders, make_product: MakeProduct
) -> None:
    seller, product = await _sized_product(make_seller, make_product)
    url = f"/api/v1/sellers/me/products/{product['id']}"
    resp = await client.patch(url, json={"sizes": [{"size": "M", "stock": 4}, {"size": "XL", "stock": 1}]}, headers=seller)
    assert resp.status_code == 400  # the chart still lists S and L, which no longer exist

    new_chart = [{"size": "M", "chest": 102}, {"size": "XL", "chest": 114}]
    resp = await client.patch(
        url, json={"sizes": [{"size": "M", "stock": 4}, {"size": "XL", "stock": 1}], "size_chart": new_chart, "stock": 99},
        headers=seller,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["sizes"] == [{"size": "M", "stock": 4}, {"size": "XL", "stock": 1}]
    assert resp.json()["stock"] == 5  # derived from the sizes, not the 99 sent


async def _deliver(client: AsyncClient, seller: Headers, order_id: int) -> None:
    url = f"/api/v1/sellers/me/orders/{order_id}/status"
    await client.patch(url, json={"status": "shipped"}, headers=seller)
    assert (await client.patch(url, json={"status": "delivered"}, headers=seller)).status_code == 200


async def _buy_delivered(client: AsyncClient, seller: Headers, customer: Headers, product_id: int, size: str) -> dict:
    await client.post(f"{CART}/items", json={"product_id": product_id, "size": size}, headers=customer)
    total = (await client.get(CART, headers=customer)).json()["totals"]["grand_total"]
    body = {"payment_method": "upi", "shipping_address": ADDRESS, "expected_total": total}
    order = (await client.post("/api/v1/orders", json=body, headers=customer)).json()["orders"][0]
    await _deliver(client, seller, order["id"])
    return order


async def test_fit_feedback_is_counted_on_the_product(
    client: AsyncClient, register_and_login: MakeHeaders, make_seller: MakeHeaders, make_product: MakeProduct
) -> None:
    seller, product = await _sized_product(make_seller, make_product)
    customer = await register_and_login()
    await _buy_delivered(client, seller, customer, product["id"], "S")
    review = {"rating": 4, "fit": "runs_small", "body": "Nice cotton but a bit snug around the chest area."}
    resp = await client.post(f"/api/v1/products/{product['id']}/reviews", json=review, headers=customer)
    assert resp.status_code == 201, resp.text
    assert resp.json()["fit"] == "runs_small"

    fit = (await client.get(f"/api/v1/products/{product['id']}")).json()["fit"]
    assert fit == {"runs_small": 1, "true_to_size": 0, "runs_large": 0, "verdict": None}  # too few to judge

    plain = await make_product(seller, title="Steel Bottle")
    await client.post(f"{CART}/items", json={"product_id": plain["id"]}, headers=customer)
    total = (await client.get(CART, headers=customer)).json()["totals"]["grand_total"]
    body = {"payment_method": "upi", "shipping_address": ADDRESS, "expected_total": total}
    order = (await client.post("/api/v1/orders", json=body, headers=customer)).json()["orders"][0]
    await _deliver(client, seller, order["id"])
    no_fit = await client.post(f"/api/v1/products/{plain['id']}/reviews", json=review, headers=customer)
    assert no_fit.status_code == 400


async def test_wrong_size_exchange_swaps_stock_and_refunds_nothing(
    client: AsyncClient,
    register_and_login: MakeHeaders,
    make_seller: MakeHeaders,
    make_product: MakeProduct,
    admin_headers: Headers,
) -> None:
    seller, product = await _sized_product(make_seller, make_product)
    customer = await register_and_login()
    order = await _buy_delivered(client, seller, customer, product["id"], "S")
    item_id = order["items"][0]["id"]
    body = {"order_item_id": item_id, "reason": "wrong_size", "description": "Too tight on the shoulders for me"}

    assert (await client.post("/api/v1/returns", json={**body, "exchange_size": "S"}, headers=customer)).status_code == 400
    assert (await client.post("/api/v1/returns", json={**body, "exchange_size": "L"}, headers=customer)).status_code == 409
    damaged = {**body, "reason": "damaged", "exchange_size": "M"}
    assert (await client.post("/api/v1/returns", json=damaged, headers=customer)).status_code == 400

    ret = await client.post("/api/v1/returns", json={**body, "exchange_size": "M"}, headers=customer)
    assert ret.status_code == 201, ret.text
    assert ret.json()["exchange_size"] == "M" and ret.json()["size"] == "S"
    assert ret.json()["refund_amount"] == "0.00"

    url = f"/api/v1/admin/returns/{ret.json()['id']}/resolve"
    approved = await client.post(url, json={"decision": "approve", "note": "Exchange approved"}, headers=admin_headers)
    assert approved.status_code == 200, approved.text
    assert "size M will be sent" in approved.json()["resolution_note"]

    stock = (await client.get(f"/api/v1/products/{product['id']}")).json()
    # S: 2 − 1 bought + 1 returned = 2; M: 3 − 1 reserved for the exchange = 2.
    assert {s["size"]: s["stock"] for s in stock["sizes"]} == {"S": 2, "M": 2, "L": 0}
    assert stock["stock"] == 4
