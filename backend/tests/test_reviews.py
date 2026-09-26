from collections.abc import AsyncIterator, Awaitable, Callable, Iterator
from typing import Any

import pytest
from httpx import AsyncClient
from langchain_core.messages import AIMessage
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.ai.llm import AssistantModels, get_assistant_models
from app.ai.tools import ToolContext, build_tools
from app.main import app
from tests.test_assistant import FailingModel, ScriptedModel

Headers = dict[str, str]
MakeHeaders = Callable[..., Awaitable[Headers]]
MakeProduct = Callable[..., Awaitable[dict[str, Any]]]
PlaceOrder = Callable[..., Awaitable[dict[str, Any]]]


@pytest.fixture
def buy_and_receive(client: AsyncClient, place_order: PlaceOrder) -> Callable[..., Awaitable[dict[str, Any]]]:
    """Customer buys one unit and the seller delivers it; returns the order."""

    async def _buy(customer: Headers, seller: Headers, product_id: int) -> dict[str, Any]:
        order = (await place_order(customer, [(product_id, 1)]))["orders"][0]
        url = f"/api/v1/sellers/me/orders/{order['id']}/status"
        await client.patch(url, json={"status": "shipped"}, headers=seller)
        resp = await client.patch(url, json={"status": "delivered"}, headers=seller)
        assert resp.status_code == 200, resp.text
        return resp.json()

    return _buy


def review_url(product_id: int) -> str:
    return f"/api/v1/products/{product_id}/reviews"


async def post_review(client: AsyncClient, headers: Headers, product_id: int, rating: int, body: str) -> dict[str, Any]:
    resp = await client.post(review_url(product_id), json={"rating": rating, "body": body}, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


async def test_only_verified_buyers_can_review(
    client: AsyncClient,
    register_and_login: MakeHeaders,
    make_seller: MakeHeaders,
    make_product: MakeProduct,
    place_order: PlaceOrder,
    buy_and_receive: Callable[..., Awaitable[dict[str, Any]]],
) -> None:
    seller = await make_seller()
    product = await make_product(seller)
    body = {"rating": 4, "body": "Nice fabric and good stitching overall."}

    stranger = await register_and_login("customer", "stranger@example.com")
    assert (await client.post(review_url(product["id"]), json=body, headers=stranger)).status_code == 403

    waiting = await register_and_login("customer", "waiting@example.com")
    await place_order(waiting, [(product["id"], 1)])  # not delivered yet
    not_yet = await client.post(review_url(product["id"]), json=body, headers=waiting)
    assert not_yet.status_code == 409
    assert "delivered" in not_yet.json()["detail"]

    buyer = await register_and_login("customer")
    await buy_and_receive(buyer, seller, product["id"])
    review = await post_review(client, buyer, product["id"], 4, body["body"])
    assert review["status"] == "published"
    assert review["verified_purchase"] is True
    assert review["reviewer"] == "Test c."  # first name + initial; never the full name or email

    again = await client.post(review_url(product["id"]), json=body, headers=buyer)
    assert again.status_code == 409
    assert (await client.post(review_url(product["id"]), json=body, headers=seller)).status_code == 403


async def test_stats_and_product_rating(
    client: AsyncClient,
    register_and_login: MakeHeaders,
    make_seller: MakeHeaders,
    make_product: MakeProduct,
    buy_and_receive: Callable[..., Awaitable[dict[str, Any]]],
) -> None:
    seller = await make_seller()
    product = await make_product(seller)
    for email, rating, text in [
        ("a@example.com", 5, "Soft cotton, perfect for hot afternoons in Pune."),
        ("b@example.com", 3, "Colour faded a little after the first wash, otherwise fine."),
    ]:
        customer = await register_and_login("customer", email)
        await buy_and_receive(customer, seller, product["id"])
        await post_review(client, customer, product["id"], rating, text)

    listing = (await client.get(review_url(product["id"]), params={"sort": "lowest"})).json()
    assert listing["stats"] == {
        "average": 4.0,
        "count": 2,
        "distribution": {"1": 0, "2": 0, "3": 1, "4": 0, "5": 1},
        "under_review": 0,
    }
    assert [r["rating"] for r in listing["items"]] == [3, 5]  # negative reviews are shown too

    detail = (await client.get(f"/api/v1/products/{product['id']}")).json()
    assert detail["rating"] == {"average": 4.0, "count": 2}
    catalogue = (await client.get("/api/v1/products")).json()
    assert catalogue["items"][0]["rating"]["count"] == 2


async def test_copy_paste_and_spam_reviews_are_flagged_not_counted(
    client: AsyncClient,
    register_and_login: MakeHeaders,
    make_seller: MakeHeaders,
    make_product: MakeProduct,
    buy_and_receive: Callable[..., Awaitable[dict[str, Any]]],
    admin_headers: Headers,
) -> None:
    seller = await make_seller()
    product = await make_product(seller)
    customers = []
    for email in ["one@example.com", "two@example.com", "three@example.com"]:
        customer = await register_and_login("customer", email)
        await buy_and_receive(customer, seller, product["id"])
        customers.append(customer)

    text = "Amazing quality kurta, best purchase ever, highly recommended to everyone!"
    first = await post_review(client, customers[0], product["id"], 5, text)
    copy = await post_review(client, customers[1], product["id"], 5, text)
    spam = await post_review(client, customers[2], product["id"], 5, "cheap at www.deals4u.in")
    assert first["status"] == "published"  # nothing to compare against yet
    assert copy["status"] == "flagged"
    assert spam["status"] == "flagged"

    # The copy also exposes the original: both are held until an admin checks them.
    listing = (await client.get(review_url(product["id"]))).json()
    assert listing["items"] == []
    assert listing["stats"]["count"] == 0
    assert listing["stats"]["under_review"] == 3

    queue = (await client.get("/api/v1/admin/reviews", headers=admin_headers)).json()
    reasons = {r["id"]: r["suspicion_reasons"] for r in queue}
    assert "duplicate_text" in reasons[copy["id"]]
    assert "duplicate_text" in reasons[first["id"]]
    assert {"contact_or_link", "short_extreme_rating"} <= set(reasons[spam["id"]])

    # Admin decides: the copy was a genuine buyer (approve), the spam goes.
    moderate = "/api/v1/admin/reviews/{}/moderate"
    ok = await client.post(moderate.format(copy["id"]), json={"action": "approve", "note": "Buyer verified by phone"}, headers=admin_headers)
    assert ok.json()["status"] == "published"
    gone = await client.post(moderate.format(spam["id"]), json={"action": "remove", "note": "Spam link"}, headers=admin_headers)
    assert gone.json()["status"] == "removed"
    again = await client.post(moderate.format(spam["id"]), json={"action": "approve", "note": "oops"}, headers=admin_headers)
    assert again.status_code == 409
    by_customer = await client.post(moderate.format(copy["id"]), json={"action": "remove", "note": "no"}, headers=customers[0])
    assert by_customer.status_code == 403

    stats = (await client.get(review_url(product["id"]))).json()["stats"]
    assert (stats["count"], stats["under_review"]) == (1, 1)  # the original still awaits a decision


async def test_trust_score_reflects_poor_ratings(
    client: AsyncClient,
    register_and_login: MakeHeaders,
    make_seller: MakeHeaders,
    make_product: MakeProduct,
    buy_and_receive: Callable[..., Awaitable[dict[str, Any]]],
) -> None:
    seller = await make_seller()
    product = await make_product(seller, stock=10)
    reviews = [
        (2, "Stitching came loose near the collar within a week."),
        (2, "Size chart was wrong, had to exchange for a bigger one."),
        (1, "Button broke on day one and the thread quality is poor."),
        (3, "Average material, looks different from the photos online."),
        (2, "Delivery was slow and the packaging arrived torn open."),
    ]
    trust = []
    for i, (rating, text) in enumerate(reviews):
        customer = await register_and_login("customer", f"buyer{i}@example.com")
        await buy_and_receive(customer, seller, product["id"])
        await post_review(client, customer, product["id"], rating, text)
        trust.append((await client.get("/api/v1/sellers/me", headers=seller)).json()["trust_score"])

    # No rating penalty until 5 reviews; then 100 − (4.0 − 2.0 avg) × 10 = 80.
    assert trust == [100, 100, 100, 100, 80]


@pytest.fixture
def use_model() -> Iterator[Callable[[Any], None]]:
    def _use(models: AssistantModels | None) -> None:
        app.dependency_overrides[get_assistant_models] = lambda: models

    yield _use
    app.dependency_overrides.pop(get_assistant_models, None)


async def test_ai_summary_is_generated_once_then_cached(
    client: AsyncClient,
    register_and_login: MakeHeaders,
    make_seller: MakeHeaders,
    make_product: MakeProduct,
    buy_and_receive: Callable[..., Awaitable[dict[str, Any]]],
    use_model: Callable[[Any], None],
) -> None:
    seller = await make_seller()
    product = await make_product(seller)
    url = f"/api/v1/products/{product['id']}/reviews/summary"

    use_model(None)
    assert (await client.get(url)).json()["status"] == "not_enough_reviews"

    texts = [
        (5, "Very breathable cotton, great for summer."),
        (4, "Good fit, colour slightly lighter than shown."),
        (4, "Comfortable and well stitched for the price."),
    ]
    for i, (rating, text) in enumerate(texts):
        customer = await register_and_login("customer", f"sum{i}@example.com")
        await buy_and_receive(customer, seller, product["id"])
        await post_review(client, customer, product["id"], rating, text)

    assert (await client.get(url)).json()["status"] == "unavailable"  # no model, nothing cached

    summary = "Buyers love the breathable cotton.\nPros:\n- Comfortable\nCons:\n- Colour a bit lighter"
    use_model(AssistantModels(primary=ScriptedModel(messages=iter([AIMessage(summary)]))))
    first = (await client.get(url)).json()
    assert first["status"] == "ready"
    assert first["summary"] == summary
    assert first["review_count"] == 3

    # Cached: served again even though the model would now fail.
    use_model(AssistantModels(primary=FailingModel(messages=iter([]))))
    assert (await client.get(url)).json()["summary"] == summary
    assert (await client.get(url, params={"language": "fr"})).status_code == 422


@pytest.fixture
async def db(session_factory: async_sessionmaker[AsyncSession]) -> AsyncIterator[AsyncSession]:
    async with session_factory() as session:
        yield session


async def test_assistant_review_insights_tool(
    client: AsyncClient,
    db: AsyncSession,
    register_and_login: MakeHeaders,
    make_seller: MakeHeaders,
    make_product: MakeProduct,
    buy_and_receive: Callable[..., Awaitable[dict[str, Any]]],
) -> None:
    seller = await make_seller()
    product = await make_product(seller)
    tools = {t.name: t for t in build_tools(ToolContext(db=db, user=None))}

    assert "no published reviews" in await tools["get_review_insights"].ainvoke({"product_id": product["id"]})
    assert "does not exist" in await tools["get_review_insights"].ainvoke({"product_id": 999})

    customer = await register_and_login("customer")
    await buy_and_receive(customer, seller, product["id"])
    await post_review(client, customer, product["id"], 4, "Nice kurta, fabric is soft and light.")
    insights = await tools["get_review_insights"].ainvoke({"product_id": product["id"]})
    assert '"average_rating": 4.0' in insights
    assert "fabric is soft" in insights
