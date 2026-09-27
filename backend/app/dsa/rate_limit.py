"""Sliding-window rate limiting (the "sliding log" variant).

A request is allowed if fewer than ``limit`` requests from the same key happened in the last
``window`` seconds. Unlike a fixed window, a burst straddling a window boundary can't double the
allowance. Two interchangeable backends:

- ``MemoryBackend``: per-key deque of timestamps; old ones are popped from the left, so each check
  is amortised O(1). Per process only.
- ``RedisBackend``: a sorted set per key (score = timestamp), trimmed and counted atomically in one
  MULTI/EXEC pipeline, so limits hold across processes/servers.
"""

import asyncio
import time
import uuid
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class Decision:
    allowed: bool
    remaining: int
    retry_after: float  # seconds until the next request would be allowed (0 if allowed)


class Backend(Protocol):
    async def hit(self, key: str, limit: int, window: float, now: float) -> Decision: ...


class MemoryBackend:
    def __init__(self, max_keys: int = 50_000) -> None:
        self._log: dict[str, deque[float]] = {}
        self._lock = asyncio.Lock()
        self._max_keys = max_keys

    async def hit(self, key: str, limit: int, window: float, now: float) -> Decision:
        async with self._lock:
            log = self._log.get(key)
            if log is None:
                if len(self._log) >= self._max_keys:  # bound memory: forget idle keys
                    self._evict_idle(now, window)
                log = self._log[key] = deque()
            while log and log[0] <= now - window:
                log.popleft()
            if len(log) >= limit:
                return Decision(False, 0, round(log[0] + window - now, 3))
            log.append(now)
            return Decision(True, limit - len(log), 0.0)

    def _evict_idle(self, now: float, window: float) -> None:
        for key in [k for k, log in self._log.items() if not log or log[-1] <= now - window]:
            del self._log[key]

    def reset(self) -> None:
        self._log.clear()


class RedisBackend:
    def __init__(self, client) -> None:  # type: ignore[no-untyped-def]  # redis.asyncio.Redis
        self._redis = client

    async def hit(self, key: str, limit: int, window: float, now: float) -> Decision:
        redis_key = f"ratelimit:{key}"
        async with self._redis.pipeline(transaction=True) as pipe:
            pipe.zremrangebyscore(redis_key, 0, now - window)
            pipe.zcard(redis_key)
            pipe.zrange(redis_key, 0, 0, withscores=True)
            _, count, oldest = await pipe.execute()
        if count >= limit:
            retry = oldest[0][1] + window - now if oldest else window
            return Decision(False, 0, round(max(retry, 0.0), 3))
        async with self._redis.pipeline(transaction=True) as pipe:
            pipe.zadd(redis_key, {f"{now}:{uuid.uuid4().hex[:8]}": now})
            pipe.expire(redis_key, int(window) + 1)
            await pipe.execute()
        return Decision(True, limit - count - 1, 0.0)


class RateLimiter:
    def __init__(self, backend: Backend, clock: Callable[[], float] = time.time, enabled: bool = True) -> None:
        self.backend = backend
        self.clock = clock
        self.enabled = enabled

    async def hit(self, key: str, limit: int, window: float) -> Decision:
        if not self.enabled:
            return Decision(True, limit, 0.0)
        return await self.backend.hit(key, limit, window, self.clock())
