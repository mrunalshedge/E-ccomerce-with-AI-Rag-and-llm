"""Weighted, undirected co-purchase graph for "frequently bought together".

Vertices are products; an edge's weight counts how often two products were bought by the same
customer (checkouts done together count double). Adjacency is a dict of dicts, so adding an edge is
O(1) and reading a product's neighbours is O(degree).
"""

from collections import defaultdict
from itertools import combinations

from app.dsa.topk import top_k


class CoPurchaseGraph:
    def __init__(self) -> None:
        self._adj: defaultdict[int, defaultdict[int, float]] = defaultdict(lambda: defaultdict(float))

    def add_basket(self, product_ids: set[int], weight: float = 1.0) -> None:
        """Connect every pair of products in one basket. O(b²) for a basket of b products."""
        for a, b in combinations(sorted(product_ids), 2):
            self._adj[a][b] += weight
            self._adj[b][a] += weight

    def weight(self, a: int, b: int) -> float:
        return self._adj.get(a, {}).get(b, 0.0)

    @property
    def edge_count(self) -> int:
        return sum(len(n) for n in self._adj.values()) // 2

    def neighbours(self, product_id: int, k: int, exclude: set[int] | None = None) -> list[tuple[int, float]]:
        """Strongest direct neighbours: O(degree · log k)."""
        exclude = (exclude or set()) | {product_id}
        edges = ((p, w) for p, w in self._adj.get(product_id, {}).items() if p not in exclude)
        return top_k(edges, k, key=lambda e: e[1])

    def recommend(self, product_id: int, k: int, exclude: set[int] | None = None) -> list[tuple[int, float]]:
        """Direct neighbours first; if fewer than k, fill with 2-hop neighbours ("bought with
        something that's bought with this") at a discounted score. A bounded two-level BFS."""
        exclude = (exclude or set()) | {product_id}
        direct = dict(self.neighbours(product_id, k=len(self._adj.get(product_id, {})), exclude=exclude))
        scores = dict(direct)
        if len(direct) < k:
            for middle, w1 in direct.items():
                for far, w2 in self._adj.get(middle, {}).items():
                    if far not in exclude and far not in direct:
                        scores[far] = scores.get(far, 0.0) + 0.5 * min(w1, w2)
        return top_k(scores.items(), k, key=lambda e: e[1])
