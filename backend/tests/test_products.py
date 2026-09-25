from collections.abc import Awaitable, Callable

from httpx import AsyncClient

SELLER_PROFILE = {
    "business_name": "Pune Handlooms Pvt Ltd",
    "contact_email": "support@punehandlooms.in",
    "phone": "+919876543210",
    "address": "12 FC Road, Shivajinagar, Pune, Maharashtra 411005",
    "gstin": "27abcde1234f1z5",
    "grievance_officer_name": "R. Kulkarni",
    "grievance_officer_email": "grievance@punehandlooms.in",
}

PRODUCT = {
    "title": "Cotton Kurta",
    "description": "Handwoven cotton kurta",
    "category": "  Clothing ",
    "base_price": "1000",
    "delivery_fee": "40",
    "platform_fee": "10",
    "stock": 5,
}

Login = Callable[..., Awaitable[dict[str, str]]]


async def test_customer_cannot_create_seller_profile(client: AsyncClient, register_and_login: Login) -> None:
    headers = await register_and_login("customer")
    resp = await client.post("/api/v1/sellers/me", json=SELLER_PROFILE, headers=headers)
    assert resp.status_code == 403


async def test_seller_needs_profile_before_listing(client: AsyncClient, register_and_login: Login) -> None:
    headers = await register_and_login("seller")
    resp = await client.post("/api/v1/products", json=PRODUCT, headers=headers)
    assert resp.status_code == 403
    assert "seller profile" in resp.json()["detail"]


async def test_seller_profile_is_unique(client: AsyncClient, register_and_login: Login) -> None:
    headers = await register_and_login("seller")
    first = await client.post("/api/v1/sellers/me", json=SELLER_PROFILE, headers=headers)
    assert first.status_code == 201
    assert first.json()["gstin"] == "27ABCDE1234F1Z5"
    assert first.json()["trust_score"] == 100
    second = await client.post("/api/v1/sellers/me", json=SELLER_PROFILE, headers=headers)
    assert second.status_code == 409


async def test_product_flow_includes_price_breakdown_and_seller_card(
    client: AsyncClient, register_and_login: Login
) -> None:
    headers = await register_and_login("seller")
    await client.post("/api/v1/sellers/me", json=SELLER_PROFILE, headers=headers)

    created = await client.post("/api/v1/products", json=PRODUCT, headers=headers)
    assert created.status_code == 201, created.text
    product = created.json()
    assert product["category"] == "clothing"
    assert product["price"]["final_price"] == "1239.00"
    assert product["price"]["gst_amount"] == "189.00"
    assert product["seller"]["business_name"] == SELLER_PROFILE["business_name"]
    assert product["seller"]["grievance_officer_email"] == SELLER_PROFILE["grievance_officer_email"]
    assert "embedding" not in product

    # Public endpoints: no auth needed.
    detail = await client.get(f"/api/v1/products/{product['id']}")
    assert detail.status_code == 200
    assert detail.json()["price"] == product["price"]

    listed = await client.get("/api/v1/products", params={"category": "CLOTHING"})
    assert listed.status_code == 200
    assert listed.json()["total"] == 1
    assert listed.json()["items"][0]["seller"]["id"] == product["seller"]["id"]

    other = await client.get("/api/v1/products", params={"category": "electronics"})
    assert other.json() == {"items": [], "total": 0, "page": 1, "page_size": 20}


async def test_pagination(client: AsyncClient, register_and_login: Login) -> None:
    headers = await register_and_login("seller")
    await client.post("/api/v1/sellers/me", json=SELLER_PROFILE, headers=headers)
    for i in range(3):
        await client.post("/api/v1/products", json={**PRODUCT, "title": f"Kurta {i}"}, headers=headers)

    page2 = await client.get("/api/v1/products", params={"page": 2, "page_size": 2})
    assert page2.json()["total"] == 3
    assert len(page2.json()["items"]) == 1


async def test_customer_cannot_create_product(client: AsyncClient, register_and_login: Login) -> None:
    headers = await register_and_login("customer")
    resp = await client.post("/api/v1/products", json=PRODUCT, headers=headers)
    assert resp.status_code == 403


async def test_unknown_product_is_404(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/products/999999")
    assert resp.status_code == 404


async def test_health(client: AsyncClient) -> None:
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok", "database": "ok"}
