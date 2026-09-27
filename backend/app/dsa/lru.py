"""LRU cache built from a hash map + doubly linked list: O(1) get, put and eviction.

(Python's OrderedDict could do this in a few lines; it's written out here to show the mechanism.)
Most recently used entries sit right after the head sentinel; the least recently used entry sits
just before the tail sentinel and is evicted first.
"""

from collections.abc import Hashable, Iterator
from typing import Generic, TypeVar

K = TypeVar("K", bound=Hashable)
V = TypeVar("V")


class _Node(Generic[K, V]):
    __slots__ = ("key", "value", "prev", "next")

    def __init__(self, key: K | None = None, value: V | None = None) -> None:
        self.key = key
        self.value = value
        self.prev: _Node[K, V] | None = None
        self.next: _Node[K, V] | None = None


class LRUCache(Generic[K, V]):
    def __init__(self, capacity: int) -> None:
        if capacity < 1:
            raise ValueError("capacity must be at least 1")
        self.capacity = capacity
        self._map: dict[K, _Node[K, V]] = {}
        self._head: _Node[K, V] = _Node()  # sentinel: most recent follows it
        self._tail: _Node[K, V] = _Node()  # sentinel: least recent precedes it
        self._head.next, self._tail.prev = self._tail, self._head

    def __len__(self) -> int:
        return len(self._map)

    def __contains__(self, key: K) -> bool:
        return key in self._map

    def _unlink(self, node: _Node[K, V]) -> None:
        assert node.prev and node.next
        node.prev.next, node.next.prev = node.next, node.prev

    def _push_front(self, node: _Node[K, V]) -> None:
        first = self._head.next
        assert first
        node.prev, node.next = self._head, first
        self._head.next = first.prev = node

    def get(self, key: K) -> V | None:
        """Value for ``key`` (and mark it most recently used), or None."""
        node = self._map.get(key)
        if node is None:
            return None
        self._unlink(node)
        self._push_front(node)
        return node.value

    def put(self, key: K, value: V) -> None:
        """Insert or update ``key`` as most recently used, evicting the LRU entry if full."""
        node = self._map.get(key)
        if node is not None:
            node.value = value
            self._unlink(node)
            self._push_front(node)
            return
        if len(self._map) >= self.capacity:
            lru = self._tail.prev
            assert lru and lru.key is not None
            self._unlink(lru)
            del self._map[lru.key]
        node = _Node(key, value)
        self._map[key] = node
        self._push_front(node)

    def keys(self) -> Iterator[K]:
        """Keys from most to least recently used."""
        node = self._head.next
        while node is not None and node is not self._tail:
            assert node.key is not None
            yield node.key
            node = node.next
