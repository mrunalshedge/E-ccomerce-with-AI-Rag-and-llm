"""Unit tests for the hand-written data structures (no database needed)."""

import pytest

from app.dsa.graph import CoPurchaseGraph
from app.dsa.lru import LRUCache
from app.dsa.rate_limit import MemoryBackend, RateLimiter
from app.dsa.topk import top_k
from app.dsa.trie import Suggestion, Trie

# ---------- trie ----------


def test_trie_ranks_by_weight_and_is_case_insensitive() -> None:
    trie = Trie(k=3)
    for text, weight in [("Kurta", 5), ("Kanjivaram Saree", 9), ("Kitchen Knife", 1), ("Kettle", 3)]:
        trie.insert(text, Suggestion(weight, text))
    assert [s.text for s in trie.complete("K")] == ["Kanjivaram Saree", "Kurta", "Kettle"]  # top 3 only
    assert [s.text for s in trie.complete("ku")] == ["Kurta"]
    assert trie.complete("x") == []
    assert [s.text for s in trie.complete("", limit=1)] == ["Kanjivaram Saree"]


def test_trie_dedupes_one_suggestion_indexed_under_several_keys() -> None:
    trie = Trie()
    kurta = Suggestion(5, "Handwoven Cotton Kurta", "product", 1)
    for key in ["handwoven cotton kurta", "cotton kurta", "kurta"]:  # title + each word suffix
        trie.insert(key, kurta)
    assert trie.complete("c") == [kurta]
    assert trie.complete("") == [kurta]  # not three copies


# ---------- LRU ----------


def test_lru_evicts_least_recently_used() -> None:
    cache: LRUCache[str, int] = LRUCache(2)
    cache.put("a", 1)
    cache.put("b", 2)
    assert cache.get("a") == 1  # "a" is now most recent
    cache.put("c", 3)  # evicts "b"
    assert "b" not in cache
    assert list(cache.keys()) == ["c", "a"]
    cache.put("a", 10)  # update moves to front without growing
    assert list(cache.keys()) == ["a", "c"] and len(cache) == 2 and cache.get("a") == 10


def test_lru_edge_cases() -> None:
    single: LRUCache[int, str] = LRUCache(1)
    single.put(1, "x")
    single.put(2, "y")
    assert list(single.keys()) == [2]
    assert single.get(1) is None
    with pytest.raises(ValueError):
        LRUCache(0)


# ---------- top-k ----------


def test_top_k_selects_best_in_order_with_stable_ties() -> None:
    items = [("a", 3), ("b", 9), ("c", 9), ("d", 1), ("e", 7)]
    assert top_k(items, 3, key=lambda x: x[1]) == [("b", 9), ("c", 9), ("e", 7)]
    assert top_k(items, 10, key=lambda x: x[1])[-1] == ("d", 1)  # k > n returns everything
    assert top_k(items, 0, key=lambda x: x[1]) == []
    assert top_k(range(100_000), 2, key=float) == [99_999, 99_998]


# ---------- co-purchase graph ----------


def test_graph_neighbours_and_two_hop_fallback() -> None:
    g = CoPurchaseGraph()
    g.add_basket({1, 2})  # kurta + dupatta
    g.add_basket({1, 2, 3})  # kurta + dupatta + saree
    g.add_basket({3, 4})  # saree + diya
    assert g.weight(1, 2) == 2 and g.weight(2, 1) == 2
    assert g.edge_count == 4
    assert g.neighbours(1, k=5) == [(2, 2.0), (3, 1.0)]
    assert g.neighbours(1, k=5, exclude={2}) == [(3, 1.0)]
    # Product 4 (diya) was never bought with 1, but it's bought with 3, which is bought with 1.
    assert [p for p, _ in g.recommend(1, k=3)] == [2, 3, 4]
    assert g.recommend(99, k=3) == []


# ---------- rate limiter ----------


class FakeClock:
    def __init__(self) -> None:
        self.now = 1_000.0

    def __call__(self) -> float:
        return self.now


async def test_sliding_window_allows_limit_then_blocks_until_oldest_expires() -> None:
    clock = FakeClock()
    limiter = RateLimiter(MemoryBackend(), clock=clock)
    decisions = []
    for _ in range(3):
        decisions.append(await limiter.hit("ip:1", limit=3, window=60))
        clock.now += 10
    assert [d.allowed for d in decisions] == [True, True, True]
    assert [d.remaining for d in decisions] == [2, 1, 0]

    blocked = await limiter.hit("ip:1", limit=3, window=60)  # t=1030
    assert not blocked.allowed
    assert blocked.retry_after == 30  # the first hit (t=1000) leaves the window at t=1060

    assert (await limiter.hit("ip:2", limit=3, window=60)).allowed  # keys are independent

    clock.now = 1_060.5  # the first request has slid out of the window
    assert (await limiter.hit("ip:1", limit=3, window=60)).allowed


async def test_sliding_window_has_no_boundary_burst() -> None:
    """A fixed window would allow 2×limit around a boundary; a sliding window doesn't."""
    clock = FakeClock()
    limiter = RateLimiter(MemoryBackend(), clock=clock)
    clock.now = 1_059.0
    assert all([(await limiter.hit("k", 2, 60)).allowed for _ in range(2)])
    clock.now = 1_061.0  # "new minute" for a fixed window, but still inside the sliding one
    assert not (await limiter.hit("k", 2, 60)).allowed


async def test_disabled_limiter_always_allows() -> None:
    limiter = RateLimiter(MemoryBackend(), enabled=False)
    assert all([(await limiter.hit("k", 1, 60)).allowed for _ in range(5)])
