"""Chat model configuration (Google Gemini via LangChain)."""

from dataclasses import dataclass, field
from functools import lru_cache

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage

from app.core.config import get_settings


@dataclass(frozen=True)
class AssistantModels:
    """The primary model plus fallbacks tried in order when it fails (e.g. "high demand" errors)."""

    primary: BaseChatModel
    fallbacks: list[BaseChatModel] = field(default_factory=list)


def _gemini(model: str, api_key: str) -> BaseChatModel:
    from langchain_google_genai import ChatGoogleGenerativeAI  # heavy import, only when needed

    # "Thinking" roughly triples latency (≈8 s → 2.5 s measured) and isn't needed for tool-grounded
    # shopping answers. Lite models reject a zero budget, so leave them at their default.
    extra = {} if "lite" in model else {"thinking_budget": 0}
    return ChatGoogleGenerativeAI(
        model=model,
        google_api_key=api_key,
        temperature=0.3,  # factual shopping answers, little creativity
        max_retries=0,  # retries/backoff are handled by the agent middleware
        timeout=30,
        **extra,
    )


@lru_cache
def _cached_models() -> AssistantModels | None:
    settings = get_settings()
    key = settings.gemini_api_key.get_secret_value() if settings.gemini_api_key else ""
    if not key:
        return None
    fallbacks = [_gemini(settings.gemini_fallback_model, key)] if settings.gemini_fallback_model else []
    return AssistantModels(primary=_gemini(settings.gemini_model, key), fallbacks=fallbacks)


def get_assistant_models() -> AssistantModels | None:
    """FastAPI dependency. ``None`` means the assistant isn't configured (no GEMINI_API_KEY).
    Tests override this with a scripted fake model."""
    return _cached_models()


def message_text(message: BaseMessage) -> str:
    """Gemini may return content as a list of parts; keep only the text."""
    content = message.content
    if isinstance(content, str):
        return content.strip()
    parts = [p if isinstance(p, str) else p.get("text", "") for p in content if isinstance(p, (str, dict))]
    return "".join(parts).strip()
