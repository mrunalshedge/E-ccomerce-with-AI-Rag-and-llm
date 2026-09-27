import json
from collections.abc import Awaitable, Callable, Iterator
from typing import Any

import pytest
from httpx import AsyncClient
from langchain_core.messages import AIMessage

from app.ai.llm import AssistantModels, get_assistant_models
from app.ai.triage import TriageDecision, apply_guardrails, rule_based
from app.main import app
from app.models.grievance import GrievanceCategory, GrievancePriority
from tests.test_assistant import FailingModel, ScriptedModel

Headers = dict[str, str]
MakeHeaders = Callable[..., Awaitable[Headers]]
MakeProduct = Callable[..., Awaitable[dict[str, Any]]]
PlaceOrder = Callable[..., Awaitable[dict[str, Any]]]
URL = "/api/v1/grievances"


def decision(**overrides: Any) -> str:
    body = {
        "category": "delivery",
        "priority": "low",
        "auto_resolve": True,
        "reply": "Your order was shipped yesterday and should arrive soon.",
        "summary": "Customer asking where order is; shipped.",
        **overrides,
    }
    return "```json\n" + json.dumps(body) + "\n```"  # fenced, as models often do


@pytest.fixture
def use_model() -> Iterator[Callable[[Any], None]]:
    def _use(models: AssistantModels | None) -> None:
        app.dependency_overrides[get_assistant_models] = lambda: models

    yield _use
    app.dependency_overrides.pop(get_assistant_models, None)


def scripted(*replies: str) -> AssistantModels:
    return AssistantModels(primary=ScriptedModel(messages=iter([AIMessage(r) for r in replies])))


# ---------- unit: guardrails & fallback ----------


def test_guardrails_never_let_ai_close_money_or_fake_item_cases() -> None:
    fake = TriageDecision(category=GrievanceCategory.WRONG_OR_FAKE_ITEM, priority=GrievancePriority.LOW,
                          auto_resolve=True, reply="ok", summary="s")
    guarded = apply_guardrails(fake)
    assert guarded.auto_resolve is False
    assert guarded.priority == GrievancePriority.HIGH  # priority floor

    info = TriageDecision(category=GrievanceCategory.DELIVERY, priority=GrievancePriority.LOW,
                          auto_resolve=True, reply="ok", summary="s")
    assert apply_guardrails(info).auto_resolve is True
    urgent = info.model_copy(update={"priority": GrievancePriority.URGENT})
    assert apply_guardrails(urgent).auto_resolve is False


@pytest.mark.parametrize(
    ("text", "category", "priority"),
    [
        ("I received a fake watch", "wrong_or_fake_item", "high"),
        ("mera paisa kat gaya par order nahi hua", "payment", "high"),
        ("मुझे नकली सामान मिला", "wrong_or_fake_item", "high"),
        ("refund not received yet", "refund", "medium"),
        ("order kab aayega? 10 din ho gaye", "delivery", "medium"),
        ("I have a question", "other", "low"),
    ],
)
def test_keyword_fallback(text: str, category: str, priority: str) -> None:
    d = rule_based(text, "en")
    assert (d.category.value, d.priority.value, d.auto_resolve) == (category, priority, False)


# ---------- API ----------


async def test_simple_question_is_answered_by_ai_and_can_be_reopened(
    client: AsyncClient,
    register_and_login: MakeHeaders,
    make_seller: MakeHeaders,
    make_product: MakeProduct,
    place_order: PlaceOrder,
    use_model: Callable[[Any], None],
) -> None:
    product = await make_product(await make_seller())
    customer = await register_and_login("customer")
    order = (await place_order(customer, [(product["id"], 1)]))["orders"][0]
    use_model(scripted(decision()))

    resp = await client.post(URL, json={"order_id": order["id"], "subject": "Where is my order?", "description": "It has been two days, where is it?"}, headers=customer)
    assert resp.status_code == 201, resp.text
    g = resp.json()
    assert g["status"] == "ai_resolved"
    assert g["category"] == "delivery"
    assert g["ai_reply"].startswith("Your order was shipped")
    assert g["acknowledged_at"] is not None
    assert g["can_reopen"] is True
    assert [e["actor"] for e in g["timeline"]] == ["customer", "ai"]

    # "This didn't help" → goes to a person.
    reopened = await client.post(f"{URL}/{g['id']}/reopen", json={"message": "Tracking hasn't moved at all"}, headers=customer)
    assert reopened.json()["status"] == "open"
    assert reopened.json()["timeline"][-1]["note"].startswith("Reopened:")
    assert (await client.post(f"{URL}/{g['id']}/reopen", json={"message": "again"}, headers=customer)).status_code == 409


async def test_ai_cannot_close_a_fake_item_complaint(
    client: AsyncClient, register_and_login: MakeHeaders, use_model: Callable[[Any], None]
) -> None:
    customer = await register_and_login("customer")
    # The model (wrongly) tries to auto-resolve and set low priority: guardrails override it.
    use_model(scripted(decision(category="wrong_or_fake_item", priority="low", reply="Sorry! Return it.")))
    g = (await client.post(URL, json={"subject": "Fake product received", "description": "The watch I got is clearly a fake copy."}, headers=customer)).json()
    assert g["status"] == "open"
    assert g["priority"] == "high"
    assert "grievance team" in g["timeline"][-1]["note"]


async def test_bad_ai_output_and_outages_fall_back_to_rules(
    client: AsyncClient, register_and_login: MakeHeaders, use_model: Callable[[Any], None]
) -> None:
    customer = await register_and_login("customer")
    body = {"subject": "Refund pending", "description": "My refund has not come for the cancelled order."}

    use_model(scripted("Sure! I think this is about a refund."))  # not JSON
    g = (await client.post(URL, json=body, headers=customer)).json()
    assert (g["category"], g["status"]) == ("refund", "open")

    use_model(AssistantModels(primary=FailingModel(messages=iter([]))))
    g = (await client.post(URL, json={**body, "language": "hi"}, headers=customer)).json()
    assert g["category"] == "refund"
    assert "शिकायत" in g["ai_reply"]  # acknowledgement in the customer's language

    use_model(None)
    assert (await client.post(URL, json=body, headers=customer)).status_code == 201


async def test_privacy_and_comments(
    client: AsyncClient,
    register_and_login: MakeHeaders,
    make_seller: MakeHeaders,
    make_product: MakeProduct,
    place_order: PlaceOrder,
    use_model: Callable[[Any], None],
) -> None:
    use_model(None)
    product = await make_product(await make_seller())
    owner = await register_and_login("customer")
    stranger = await register_and_login("customer", "stranger@example.com")
    order = (await place_order(owner, [(product["id"], 1)]))["orders"][0]

    # Can't attach someone else's order.
    other = await client.post(URL, json={"order_id": order["id"], "subject": "Not my order", "description": "Trying someone else's order"}, headers=stranger)
    assert other.status_code == 404

    g = (await client.post(URL, json={"order_id": order["id"], "subject": "Damaged box", "description": "The box arrived torn and wet."}, headers=owner)).json()
    assert (await client.get(f"{URL}/{g['id']}", headers=stranger)).status_code == 404
    commented = await client.post(f"{URL}/{g['id']}/comments", json={"message": "Adding photo details: corner crushed"}, headers=owner)
    assert commented.json()["timeline"][-1]["note"] == "Adding photo details: corner crushed"
    assert [x["id"] for x in (await client.get(URL, headers=owner)).json()] == [g["id"]]
    assert (await client.get(URL, headers=stranger)).json() == []


async def test_admin_queue_update_and_overview(
    client: AsyncClient, register_and_login: MakeHeaders, admin_headers: Headers, use_model: Callable[[Any], None]
) -> None:
    use_model(None)
    customer = await register_and_login("customer")
    low = (await client.post(URL, json={"subject": "General question", "description": "How do I change my name?"}, headers=customer)).json()
    high = (await client.post(URL, json={"subject": "Charged twice", "description": "Payment deducted twice for one order"}, headers=customer)).json()

    queue = (await client.get("/api/v1/admin/grievances", headers=admin_headers)).json()
    assert [g["id"] for g in queue] == [high["id"], low["id"]]  # most urgent first
    assert queue[0]["customer_email"] == "customer@example.com"
    assert queue[0]["triaged_by"] == "rules"

    overview = (await client.get("/api/v1/admin/overview", headers=admin_headers)).json()
    assert (overview["open_grievances"], overview["urgent_or_high"], overview["overdue_grievances"]) == (2, 1, 0)

    url = f"/api/v1/admin/grievances/{high['id']}/update"
    await client.post(url, json={"status": "in_progress", "note": "Checking with the payment gateway"}, headers=admin_headers)
    done = await client.post(url, json={"status": "resolved", "note": "Duplicate charge refunded to your UPI."}, headers=admin_headers)
    assert done.json()["status"] == "resolved"
    assert done.json()["resolved_at"] is not None
    assert (await client.post(url, json={"status": "resolved", "note": "again"}, headers=admin_headers)).status_code == 409
    assert (await client.post(url, json={"status": "resolved", "note": "hack"}, headers=customer)).status_code == 403

    seen = (await client.get(f"{URL}/{high['id']}", headers=customer)).json()
    assert [e["actor"] for e in seen["timeline"]] == ["customer", "ai", "admin", "admin"]
    assert seen["can_reopen"] is True
