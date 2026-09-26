"""Assistant tests with a scripted fake chat model: fast, free, and deterministic.
The real Gemini path is covered by tests/test_ai_live.py (opt-in)."""

from collections.abc import AsyncIterator, Awaitable, Callable, Iterator
from typing import Any

import pytest
from httpx import AsyncClient
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.ai.assistant import _mentioned, _script_hint
from app.ai.llm import AssistantModels, get_assistant_models
from app.ai.tools import ToolContext, build_tools
from app.main import app
from app.services.user_service import get_user_by_email

CHAT = "/api/v1/assistant/chat"
MakeHeaders = Callable[..., Awaitable[dict[str, str]]]
MakeProduct = Callable[..., Awaitable[dict[str, Any]]]


class ScriptedModel(GenericFakeChatModel):
    """Replays prepared messages (including tool calls); tools are bound by the agent."""

    def bind_tools(self, tools: Any, **kwargs: Any) -> "ScriptedModel":
        return self


class FailingModel(ScriptedModel):
    def _generate(self, *args: Any, **kwargs: Any) -> Any:
        raise RuntimeError("503 UNAVAILABLE: high demand")


def tool_call(name: str, **args: Any) -> AIMessage:
    return AIMessage(content="", tool_calls=[{"name": name, "args": args, "id": f"call-{name}"}])


@pytest.fixture
def use_model() -> Iterator[Callable[[Any], None]]:
    def _use(models: AssistantModels | None) -> None:
        app.dependency_overrides[get_assistant_models] = lambda: models

    yield _use
    app.dependency_overrides.pop(get_assistant_models, None)


async def test_answers_from_catalogue_and_returns_mentioned_products(
    client: AsyncClient, make_seller: MakeHeaders, make_product: MakeProduct, use_model: Callable[[Any], None]
) -> None:
    seller = await make_seller()
    await make_product(seller)  # Cotton Kurta
    await make_product(seller, title="Cotton Dupatta", description="Light cotton dupatta", base_price="449")
    use_model(
        AssistantModels(
            primary=ScriptedModel(
                messages=iter(
                    [
                        tool_call("search_products", query="cotton kurta"),
                        AIMessage("The Cotton Kurta costs ₹1,239 all-inclusive from Pune Handlooms Pvt Ltd."),
                    ]
                )
            )
        )
    )

    resp = await client.post(CHAT, json={"message": "kurta dikhao", "language": "hi"})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "Cotton Kurta" in body["reply"]
    # Only the product the reply talks about becomes a card, with real DB prices.
    assert [p["title"] for p in body["products"]] == ["Cotton Kurta"]
    assert body["products"][0]["price"]["final_price"] == "1239.00"


async def test_provider_failure_is_a_friendly_503(client: AsyncClient, use_model: Callable[[Any], None]) -> None:
    use_model(AssistantModels(primary=FailingModel(messages=iter([]))))
    resp = await client.post(CHAT, json={"message": "hello"})
    assert resp.status_code == 503
    assert "busy" in resp.json()["detail"]


async def test_not_configured_is_503(client: AsyncClient, use_model: Callable[[Any], None]) -> None:
    use_model(None)
    resp = await client.post(CHAT, json={"message": "hello"})
    assert resp.status_code == 503
    assert "GEMINI_API_KEY" in resp.json()["detail"]


async def test_request_validation(client: AsyncClient) -> None:
    assert (await client.post(CHAT, json={"message": ""})).status_code == 422
    assert (await client.post(CHAT, json={"message": "x" * 1001})).status_code == 422
    assert (await client.post(CHAT, json={"message": "hi", "language": "fr"})).status_code == 422


@pytest.fixture
async def db(session_factory: async_sessionmaker[AsyncSession]) -> AsyncIterator[AsyncSession]:
    async with session_factory() as session:
        yield session


async def _tool(ctx: ToolContext, name: str, **args: Any) -> str:
    tools = {t.name: t for t in build_tools(ctx)}
    return str(await tools[name].ainvoke(args))


async def test_order_tools_require_a_logged_in_customer(
    db: AsyncSession,
    register_and_login: MakeHeaders,
    make_seller: MakeHeaders,
    make_product: MakeProduct,
    place_order: Callable[..., Awaitable[dict[str, Any]]],
) -> None:
    anonymous = await _tool(ToolContext(db=db, user=None), "get_my_orders")
    assert "not logged in" in anonymous

    product = await make_product(await make_seller())
    customer_headers = await register_and_login("customer")
    order = (await place_order(customer_headers, [(product["id"], 1)]))["orders"][0]
    customer = await get_user_by_email(db, "customer@example.com")
    assert customer is not None

    ctx = ToolContext(db=db, user=customer)
    orders = await _tool(ctx, "get_my_orders")
    assert f'"order_id": {order["id"]}' in orders
    status = await _tool(ctx, "get_order_status", order_id=order["id"])
    assert '"status": "placed"' in status
    assert "not found" in await _tool(ctx, "get_order_status", order_id=9999)


async def test_product_tools_record_what_the_model_saw(
    db: AsyncSession, make_seller: MakeHeaders, make_product: MakeProduct
) -> None:
    product = await make_product(await make_seller())
    ctx = ToolContext(db=db, user=None)
    details = await _tool(ctx, "get_product_details", product_id=product["id"])
    assert '"final_price": "1239.00"' in details
    assert "grievance_officer" in details
    await _tool(ctx, "search_products", query="cotton kurta")
    assert ctx.surfaced_products() == [(product["id"], "Cotton Kurta")]
    assert "7 days" in await _tool(ctx, "get_return_policy")


def test_language_hint() -> None:
    assert "Devanagari" in _script_hint("मुझे कुर्ता चाहिए")
    assert "Hinglish" in _script_hint("sasta charger hai kya?")
    assert "English" in _script_hint("Is the saree returnable?")


def test_mentioned_products() -> None:
    products = [(1, "Handwoven Cotton Kurta"), (2, "Brass Diya Set of 4")]
    assert _mentioned("Try the **Handwoven Cotton Kurta**!", products) == [1]
    assert _mentioned("दिवाली के लिए Brass Diya उपलब्ध है", products) == [2]
    assert _mentioned("Nothing matched.", products) == []
