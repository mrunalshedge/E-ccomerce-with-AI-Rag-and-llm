from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.product import ProductRead


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=4000)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=1000)
    # Earlier turns of this conversation (the server keeps no chat state).
    history: list[ChatMessage] = Field(default_factory=list, max_length=20)
    language: Literal["en", "hi", "mr"] = "en"


class ChatResponse(BaseModel):
    reply: str
    products: list[ProductRead]
