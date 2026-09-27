"""Prefix trie for search autocomplete.

Each node caches the top-K suggestions of its subtree, so answering a keystroke is O(P) where P is
the prefix length, independent of catalogue size. Inserting costs O(L · K) (L = key length),
because every node on the path may update its small cached list.
"""

from dataclasses import dataclass, field


@dataclass(frozen=True, order=True)
class Suggestion:
    weight: float
    text: str
    kind: str = "product"  # "product" | "category" | "seller"
    ref: int | str | None = None  # product id / category slug / seller id


@dataclass
class _Node:
    children: dict[str, "_Node"] = field(default_factory=dict)
    top: list[Suggestion] = field(default_factory=list)  # best first, at most K


class Trie:
    def __init__(self, k: int = 8) -> None:
        self.k = k
        self._root = _Node()
        self.size = 0

    def insert(self, key: str, suggestion: Suggestion) -> None:
        """Index ``suggestion`` under ``key`` (case-insensitive)."""
        node = self._root
        self._offer(node, suggestion)
        for char in key.lower():
            node = node.children.setdefault(char, _Node())
            self._offer(node, suggestion)
        self.size += 1

    def _offer(self, node: _Node, suggestion: Suggestion) -> None:
        # One suggestion may reach a node via several keys (title + each word): keep it once.
        if any(s.text == suggestion.text and s.kind == suggestion.kind for s in node.top):
            return
        node.top.append(suggestion)
        node.top.sort(key=lambda s: (-s.weight, s.text))
        del node.top[self.k :]

    def complete(self, prefix: str, limit: int | None = None) -> list[Suggestion]:
        """Best suggestions whose key starts with ``prefix``. O(len(prefix))."""
        node = self._root
        for char in prefix.lower():
            node = node.children.get(char)  # type: ignore[assignment]
            if node is None:
                return []
        return node.top[: limit or self.k]
