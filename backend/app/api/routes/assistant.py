from typing import Annotated

from fastapi import APIRouter, Depends

from app.ai import assistant
from app.ai.llm import AssistantModels, get_assistant_models
from app.api.deps import DbSession, OptionalUser
from app.core.rate_limit import rate_limit
from app.schemas.assistant import ChatRequest, ChatResponse
from app.services import product_service

router = APIRouter(prefix="/assistant", tags=["assistant"])


@router.post(
    "/chat",
    response_model=ChatResponse,
    dependencies=[Depends(rate_limit("assistant", limit=20, window_seconds=60, per="user"))],
)
async def chat(
    data: ChatRequest,
    db: DbSession,
    user: OptionalUser,
    models: Annotated[AssistantModels | None, Depends(get_assistant_models)],
) -> ChatResponse:
    """Ask the AI shopping assistant (English, हिंदी, मराठी or Hinglish).

    It answers from live catalogue and order data via tools, and returns the products it talked
    about as cards with real prices. Logged-in customers can also ask about their orders.
    Returns **503** if the AI provider is unavailable or not configured.
    """
    reply, product_ids = await assistant.chat(db, user, models, data.message, data.history, data.language)
    products = await product_service.get_products_by_ids(db, product_ids)
    return ChatResponse(reply=reply, products=await product_service.to_product_reads(db, products))
