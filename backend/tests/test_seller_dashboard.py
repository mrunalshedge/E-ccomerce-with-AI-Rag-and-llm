from collections.abc import Awaitable, Callable
from typing import Any

from httpx import AsyncClient

Headers = dict[str, str]
MakeHeaders = Callable[..., Awaitable[Headers]]
MakeProduct = Callable[..., Awaitable[dict[str, Any]]]
PlaceOrder = Callable[..., Awaitable[dict[str, Any]]]
ME = "/api/v1/sellers/me"


async def test_price_preview_uses_the_store_pricing_rule(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/pricing/preview", params={"base_price": "1000", "delivery_fee": "40", "platform_fee": "10"})
    assert resp.status_code == 200
    assert resp.json()["final_price"] == "1239.00"
    assert (await client.get("/api/v1/pricing/preview", params={"base_price": "-1"})).status_code == 422


async def test_seller_edits_own_products_only(
    client: AsyncClient, make_seller: MakeHeaders, make_product: MakeProduct
) -> None:
    seller = await make_seller()
    rival = await make_seller("rival@example.com", "Rival Traders")
    product = await make_product(seller, stock=0)
    await make_product(seller, title="Silk Stole", stock=20)

    mine = (await client.get(f"{ME}/products", headers=seller)).json()
    assert [p["title"] for p in mine] == ["Cotton Kurta", "Silk Stole"]  # out of stock first
    assert (await client.get(f"{ME}/products", headers=rival)).json() == []

    url = f"{ME}/products/{product['id']}"
    resp = await client.patch(url, json={"base_price": "1100", "stock": 12, "title": None}, headers=seller)
    assert resp.status_code == 200
    body = resp.json()
    assert body["title"] == "Cotton Kurta"  # null means "unchanged" for required fields
    assert body["stock"] == 12
    assert body["price"]["final_price"] == "1357.00"  # (1100 + 40 + 10) × 1.18

    renamed = await client.patch(url, json={"title": "Handloom Cotton Kurta", "category": " Ethnic Wear "}, headers=seller)
    assert renamed.json()["category"] == "ethnic wear"
    found = (await client.get("/api/v1/search/suggest", params={"q": "handloom"})).json()
    assert [s["text"] for s in found] == ["Handloom Cotton Kurta"]  # autocomplete refreshed

    assert (await client.patch(url, json={"stock": 1}, headers=rival)).status_code == 404
    assert (await client.patch(url, json={"stock": -1}, headers=seller)).status_code == 422
    assert (await client.patch(f"{ME}/products/999", json={"stock": 1}, headers=seller)).status_code == 404


async def test_dashboard_numbers_trust_breakdown_and_reviews(
    client: AsyncClient,
    register_and_login: MakeHeaders,
    make_seller: MakeHeaders,
    make_product: MakeProduct,
    place_order: PlaceOrder,
) -> None:
    seller = await make_seller()
    product = await make_product(seller, stock=3)
    customer = await register_and_login("customer")
    first = (await place_order(customer, [(product["id"], 1)]))["orders"][0]
    await place_order(customer, [(product["id"], 1)])  # stays "placed" (to ship)

    status_url = f"{ME}/orders/{first['id']}/status"
    await client.patch(status_url, json={"status": "shipped"}, headers=seller)
    await client.patch(status_url, json={"status": "delivered"}, headers=seller)
    review = await client.post(
        f"/api/v1/products/{product['id']}/reviews",
        json={"rating": 4, "body": "Good fabric, fits well and colour is as shown."},
        headers=customer,
    )
    assert review.status_code == 201

    dash = (await client.get(f"{ME}/dashboard", headers=seller)).json()
    assert dash["to_ship"] == 1
    assert dash["in_transit"] == 0
    assert dash["delivered_30d"] == 1
    assert dash["revenue_30d"] == "2478.00"
    assert (dash["products"], dash["low_stock"]) == (1, 1)  # 1 left in stock
    assert (dash["average_rating"], dash["review_count"]) == (4.0, 1)
    assert dash["trust"] == {
        "score": 100.0,
        "wrong_or_fake_returns": 0,
        "return_penalty": 0.0,
        "average_rating": 4.0,
        "review_count": 1,
        "rating_penalty": 0.0,
        "min_reviews_for_rating_penalty": 5,
        "rating_target": 4.0,
    }

    reviews = (await client.get(f"{ME}/reviews", headers=seller)).json()
    assert [(r["product_title"], r["rating"], r["reviewer"]) for r in reviews] == [("Cotton Kurta", 4, "Test c.")]
    assert (await client.get(f"{ME}/dashboard", headers=customer)).status_code == 403
