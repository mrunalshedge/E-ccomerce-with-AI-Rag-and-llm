"""3D models and wrist try-on: input validation, and sellers can change or remove them."""

from collections.abc import Awaitable, Callable
from typing import Any

from httpx import AsyncClient

Headers = dict[str, str]
MakeHeaders = Callable[..., Awaitable[Headers]]
MakeProduct = Callable[..., Awaitable[dict[str, Any]]]

GLB = "https://example.com/models/lamp.glb"


async def test_model_link_must_be_https_gltf(client: AsyncClient, make_seller: MakeHeaders) -> None:
    seller = await make_seller()
    body = {"title": "Table Lamp", "description": "Glass lamp", "category": "home", "base_price": "999"}
    for bad in ("http://example.com/lamp.glb", "https://example.com/lamp.obj", "https://example.com/lamp"):
        resp = await client.post("/api/v1/products", json={**body, "model_url": bad}, headers=seller)
        assert resp.status_code == 422, bad

    resp = await client.post(
        "/api/v1/products", json={**body, "model_url": GLB, "model_credit": "Me, CC BY 4.0"}, headers=seller
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["model_url"] == GLB
    assert resp.json()["model_credit"] == "Me, CC BY 4.0"


async def test_seller_can_change_and_remove_the_model(
    client: AsyncClient, make_seller: MakeHeaders, make_product: MakeProduct
) -> None:
    seller = await make_seller()
    product = await make_product(seller)
    assert product["model_url"] is None
    url = f"/api/v1/sellers/me/products/{product['id']}"

    added = await client.patch(url, json={"model_url": GLB}, headers=seller)
    assert added.json()["model_url"] == GLB
    untouched = await client.patch(url, json={"title": "Cotton Kurta v2"}, headers=seller)
    assert untouched.json()["model_url"] == GLB  # omitted = unchanged
    removed = await client.patch(url, json={"model_url": None, "model_credit": None}, headers=seller)
    assert removed.json()["model_url"] is None


TRY_ON = {"kind": "wrist", "case_mm": 40, "dial_color": "#f4f4f2", "case_color": "#c7cad0", "strap_color": "#16181b"}


async def test_wrist_try_on_settings_are_validated_and_clearable(client: AsyncClient, make_seller: MakeHeaders) -> None:
    seller = await make_seller()
    body = {"title": "Steel Watch", "description": "Analog watch", "category": "accessories", "base_price": "1799"}
    for bad in ({**TRY_ON, "case_mm": 90}, {**TRY_ON, "dial_color": "red"}, {**TRY_ON, "kind": "face"}):
        resp = await client.post("/api/v1/products", json={**body, "try_on": bad}, headers=seller)
        assert resp.status_code == 422, bad

    created = await client.post("/api/v1/products", json={**body, "try_on": TRY_ON}, headers=seller)
    assert created.status_code == 201, created.text
    assert created.json()["try_on"] == TRY_ON

    url = f"/api/v1/sellers/me/products/{created.json()['id']}"
    resized = await client.patch(url, json={"try_on": {**TRY_ON, "case_mm": 44}}, headers=seller)
    assert resized.json()["try_on"]["case_mm"] == 44
    off = await client.patch(url, json={"try_on": None}, headers=seller)
    assert off.json()["try_on"] is None
