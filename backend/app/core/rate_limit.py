"""App-wide rate limiter and the ``rate_limit(...)`` FastAPI dependency.

Redis is used when REDIS_URL answers a ping at startup (limits then hold across processes);
otherwise an in-memory sliding log is used, which is fine for a single dev server.
"""

import logging
import math
from collections.abc import Awaitable, Callable
from typing import Literal

import jwt
from fastapi import HTTPException, Request, status

from app.core.config import get_settings
from app.core.security import decode_access_token
from app.dsa.rate_limit import MemoryBackend, RateLimiter, RedisBackend

logger = logging.getLogger(__name__)

limiter = RateLimiter(MemoryBackend(), enabled=get_settings().rate_limit_enabled)


async def init_rate_limiter() -> str:
    """Switch to Redis if it's reachable. Returns the backend name (for the startup log)."""
    if not limiter.enabled:
        return "disabled"
    try:
        from redis.asyncio import Redis

        client = Redis.from_url(get_settings().redis_url, socket_connect_timeout=0.5, socket_timeout=0.5)
        await client.ping()
    except Exception:
        logger.info("Redis not reachable; using in-memory rate limiting")
        return "memory"
    limiter.backend = RedisBackend(client)
    return "redis"


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def rate_limit(
    scope: str, limit: int, window_seconds: int, per: Literal["ip", "user"] = "ip"
) -> Callable[[Request], Awaitable[None]]:
    """Dependency factory: at most ``limit`` requests per ``window_seconds`` for each IP (or each
    logged-in user, falling back to IP). Over the limit → 429 with a Retry-After header."""

    async def check(request: Request) -> None:
        key = f"ip:{_client_ip(request)}"
        if per == "user":
            # Key on the user id inside the token (not the token), so logging in again doesn't
            # reset the limit. Invalid/absent tokens fall back to the IP.
            token = request.headers.get("authorization", "").removeprefix("Bearer ").strip()
            try:
                key = f"user:{decode_access_token(token)['sub']}" if token else key
            except (jwt.PyJWTError, KeyError):
                pass
        decision = await limiter.hit(f"{scope}:{key}", limit, window_seconds)
        if not decision.allowed:
            retry = max(1, math.ceil(decision.retry_after))
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Too many requests. Please try again in {retry} seconds.",
                headers={"Retry-After": str(retry)},
            )

    return check
