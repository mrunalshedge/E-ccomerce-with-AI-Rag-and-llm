from collections.abc import Awaitable, Callable, Iterator
from typing import Any

import pytest
from httpx import AsyncClient

from app.core.rate_limit import limiter
from app.dsa.rate_limit import MemoryBackend

Headers = dict[str, str]
MakeHeaders = Callable[..., Awaitable[Headers]]
MakeProduct = Callable[..., Awaitable[dict[str, Any]]]
PlaceOrder = Callable[..., Awaitable[dict[str, Any]]]


async def _catalogue(make_seller: MakeHeaders, make_product: MakeProduct) -> dict[str, int]:
    seller = await make_seller()
    ids = {}
    for title, category, stock in [
        ("Handwoven Cotton Kurta", "clothing", 10),
        ("Cotton Dupatta", "clothing", 10),
        ("Kanjivaram Silk Saree", "clothing", 10),
        ("Brass Diya Set", "home", 10),
        ("Sold Out Lamp", "home", 0),
    ]:
        ids[title] = (await make_product(seller, title=title, category=category, stock=stock))["id"]
    return ids


async def test_autocomplete_matches_any_word_categories_and_sellers(
    client: AsyncClient, make_seller: MakeHeaders, make_product: MakeProduct
) -> None:
    await _catalogue(make_seller, make_product)
    texts = lambda resp: [(s["text"], s["kind"]) for s in resp.json()]  # noqa: E731

    kurta = await client.get("/api/v1/search/suggest", params={"q": "kur"})
    assert texts(kurta) == [("Handwoven Cotton Kurta", "product")]
    assert kurta.json()[0]["product_id"] is not None

    cotton = texts(await client.get("/api/v1/search/suggest", params={"q": "COTTON"}))
    assert {t for t, _ in cotton} == {"Handwoven Cotton Kurta", "Cotton Dupatta"}  # word inside title too

    clothing = (await client.get("/api/v1/search/suggest", params={"q": "cl"})).json()
    assert clothing[0] == {"text": "clothing", "kind": "category", "product_id": None, "category": "clothing"}

    seller = texts(await client.get("/api/v1/search/suggest", params={"q": "pune"}))
    assert seller == [("Pune Handlooms Pvt Ltd", "seller")]
    assert (await client.get("/api/v1/search/suggest", params={"q": "  "})).json() == []


async def test_bought_together_from_real_orders(
    client: AsyncClient,
    register_and_login: MakeHeaders,
    make_seller: MakeHeaders,
    make_product: MakeProduct,
    place_order: PlaceOrder,
) -> None:
    ids = await _catalogue(make_seller, make_product)
    kurta, dupatta, saree = ids["Handwoven Cotton Kurta"], ids["Cotton Dupatta"], ids["Kanjivaram Silk Saree"]
    a = await register_and_login("customer", "a@example.com")
    b = await register_and_login("customer", "b@example.com")
    await place_order(a, [(kurta, 1), (dupatta, 1)])  # same cart: weight 2
    await place_order(b, [(kurta, 1)])
    await place_order(b, [(saree, 1)])  # separate cart, same customer: weight 1

    together = (await client.get(f"/api/v1/products/{kurta}/bought-together")).json()
    assert [p["title"] for p in together] == ["Cotton Dupatta", "Kanjivaram Silk Saree"]
    # 2-hop: dupatta was never bought with saree, but both were bought with the kurta.
    hop = (await client.get(f"/api/v1/products/{dupatta}/bought-together")).json()
    assert [p["title"] for p in hop] == ["Handwoven Cotton Kurta", "Kanjivaram Silk Saree"]
    assert (await client.get("/api/v1/products/999/bought-together")).status_code == 404


async def test_recently_viewed_is_an_lru(
    client: AsyncClient, register_and_login: MakeHeaders, make_seller: MakeHeaders, make_product: MakeProduct
) -> None:
    ids = list((await _catalogue(make_seller, make_product)).values())
    customer = await register_and_login("customer")
    for pid in [ids[0], ids[1], ids[2], ids[0]]:  # re-viewing ids[0] moves it to the front
        resp = await client.post(f"/api/v1/me/recently-viewed/{pid}", headers=customer)
        assert resp.status_code == 204
    viewed = (await client.get("/api/v1/me/recently-viewed", headers=customer)).json()
    assert [p["id"] for p in viewed] == [ids[0], ids[2], ids[1]]
    assert (await client.get("/api/v1/me/recently-viewed")).status_code == 401
    assert (await client.post("/api/v1/me/recently-viewed/999", headers=customer)).status_code == 404


async def test_recommendations_are_personal_and_explained(
    client: AsyncClient,
    register_and_login: MakeHeaders,
    make_seller: MakeHeaders,
    make_product: MakeProduct,
    place_order: PlaceOrder,
) -> None:
    ids = await _catalogue(make_seller, make_product)
    kurta, dupatta = ids["Handwoven Cotton Kurta"], ids["Cotton Dupatta"]
    buyer = await register_and_login("customer", "buyer@example.com")
    await place_order(buyer, [(kurta, 1), (dupatta, 1)])

    # A guest who viewed the kurta: the dupatta (bought with it) comes first.
    guest = (await client.get("/api/v1/recommendations", params={"seen": str(kurta)})).json()
    assert guest[0]["product"]["title"] == "Cotton Dupatta"
    assert guest[0]["reason"] == "bought_together"
    assert kurta not in [r["product"]["id"] for r in guest]  # not what they're looking at
    assert "Sold Out Lamp" not in [r["product"]["title"] for r in guest]  # in stock only

    # The buyer isn't recommended what they already bought.
    mine = (await client.get("/api/v1/recommendations", headers=buyer)).json()
    assert {kurta, dupatta}.isdisjoint(r["product"]["id"] for r in mine)
    assert mine[0]["reason"] == "similar_interest"  # more clothing

    # No history at all: popular products.
    anon = (await client.get("/api/v1/recommendations", params={"limit": 2})).json()
    assert [r["reason"] for r in anon] == ["popular", "popular"]
    assert anon[0]["product"]["title"] in {"Handwoven Cotton Kurta", "Cotton Dupatta"}  # best sellers


@pytest.fixture
def rate_limits_on() -> Iterator[None]:
    original = limiter.backend
    limiter.backend, limiter.enabled = MemoryBackend(), True
    yield
    limiter.backend, limiter.enabled = original, False


async def test_login_is_rate_limited_with_retry_after(client: AsyncClient, rate_limits_on: None) -> None:
    form = {"username": "nobody@example.com", "password": "wrong-password"}
    codes = [(await client.post("/api/v1/auth/login", data=form)).status_code for _ in range(10)]
    assert codes == [401] * 10
    blocked = await client.post("/api/v1/auth/login", data=form)
    assert blocked.status_code == 429
    assert int(blocked.headers["Retry-After"]) >= 1
    assert "Too many requests" in blocked.json()["detail"]
