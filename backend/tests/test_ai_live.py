"""Opt-in smoke test against the real Gemini API (embeddings stay fake, see conftest).

Run with:  RUN_LIVE_AI=1 pytest tests/test_ai_live.py   (uses a few free-tier requests)
"""

import os
from collections.abc import Awaitable, Callable
from typing import Any

import pytest
from httpx import AsyncClient

pytestmark = [
    pytest.mark.live,
    pytest.mark.skipif(os.environ.get("RUN_LIVE_AI") != "1", reason="set RUN_LIVE_AI=1 to call the real Gemini API"),
]


async def test_real_assistant_answers_hinglish_from_catalogue(
    client: AsyncClient, make_seller: Callable[..., Awaitable[dict[str, str]]], make_product: Callable[..., Awaitable[dict[str, Any]]]
) -> None:
    seller = await make_seller()
    await make_product(
        seller,
        title="Wireless Earbuds",
        description="Bluetooth earbuds with noise cancellation for music and calls",
        category="electronics",
        base_price="1299",
    )
    resp = await client.post("/api/v1/assistant/chat", json={"message": "gaana sunne ke liye kuch dikhao"})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert [p["title"] for p in body["products"]] == ["Wireless Earbuds"]
    assert "₹" in body["reply"]
