from collections.abc import Awaitable, Callable
from typing import Any

from httpx import AsyncClient

SEARCH = "/api/v1/search"
MakeHeaders = Callable[..., Awaitable[dict[str, str]]]
MakeProduct = Callable[..., Awaitable[dict[str, Any]]]


async def _catalogue(make_seller: MakeHeaders, make_product: MakeProduct) -> None:
    seller = await make_seller()
    await make_product(seller)  # "Cotton Kurta", ₹1239
    await make_product(
        seller,
        title="Wireless Earbuds",
        description="Bluetooth earbuds with noise cancellation for music",
        category="electronics",
        base_price="1299",
    )
    await make_product(
        seller,
        title="Kanjivaram Pure Silk Saree",
        description="Handwoven zari border saree",
        base_price="8999",
    )


async def test_finds_products_by_words_and_meaning(
    client: AsyncClient, make_seller: MakeHeaders, make_product: MakeProduct
) -> None:
    await _catalogue(make_seller, make_product)

    kurta = (await client.get(SEARCH, params={"q": "cotton kurta"})).json()
    assert kurta["items"][0]["title"] == "Cotton Kurta"
    assert kurta["items"][0]["price"]["final_price"] == "1239.00"  # full product cards

    music = (await client.get(SEARCH, params={"q": "earbuds for music"})).json()
    assert [p["title"] for p in music["items"]] == ["Wireless Earbuds"]

    # Words, not the exact phrase: "Kanjivaram saree" finds "Kanjivaram Pure Silk Saree".
    saree = (await client.get(SEARCH, params={"q": "Kanjivaram saree"})).json()
    assert saree["items"][0]["title"] == "Kanjivaram Pure Silk Saree"


async def test_filters_and_no_match(client: AsyncClient, make_seller: MakeHeaders, make_product: MakeProduct) -> None:
    await _catalogue(make_seller, make_product)

    electronics = (await client.get(SEARCH, params={"q": "handwoven", "category": "electronics"})).json()
    assert electronics["items"] == []

    budget = (await client.get(SEARCH, params={"q": "saree kurta", "max_price": "2000"})).json()
    assert [p["title"] for p in budget["items"]] == ["Cotton Kurta"]  # saree is ₹9k+

    nothing = (await client.get(SEARCH, params={"q": "laptop"})).json()
    assert nothing == {"query": "laptop", "items": [], "total": 0}


async def test_query_is_required(client: AsyncClient) -> None:
    assert (await client.get(SEARCH)).status_code == 422
    assert (await client.get(SEARCH, params={"q": ""})).status_code == 422
