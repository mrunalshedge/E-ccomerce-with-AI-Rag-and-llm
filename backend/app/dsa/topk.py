"""Top-K selection with a bounded min-heap: O(n log k) time, O(k) memory.

Sorting all n candidates would be O(n log n); for "best 8 of 10,000 products" the heap keeps only
the k best seen so far and replaces its smallest element when a better one arrives.
"""

import heapq
from collections.abc import Callable, Iterable
from itertools import count
from typing import TypeVar

T = TypeVar("T")


def top_k(items: Iterable[T], k: int, key: Callable[[T], float]) -> list[T]:
    """The ``k`` items with the highest ``key``, best first. Ties keep input order."""
    if k <= 0:
        return []
    heap: list[tuple[float, int, T]] = []  # (score, -arrival, item): the root is the worst kept item
    arrival = count()
    for item in items:
        entry = (key(item), -next(arrival), item)
        if len(heap) < k:
            heapq.heappush(heap, entry)
        elif entry[:2] > heap[0][:2]:
            heapq.heapreplace(heap, entry)
    return [item for _, _, item in sorted(heap, key=lambda e: (e[0], e[1]), reverse=True)]
