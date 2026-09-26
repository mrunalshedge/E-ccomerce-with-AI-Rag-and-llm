"""Text embeddings for semantic search.

Production uses a small multilingual model (paraphrase-multilingual-MiniLM-L12-v2, 384 dims) that
runs locally on CPU via fastembed/ONNX: free, offline after the first download, and it understands
Hindi and Marathi as well as English. Tests use ``HashingEmbedder``, a deterministic bag-of-words
stand-in that needs no model download.
"""

import hashlib
import logging
import math
import os
import re
import threading
from functools import lru_cache
from typing import Protocol

from anyio import to_thread

from app.core.config import get_settings
from app.models.product import EMBEDDING_DIM, Product

logger = logging.getLogger(__name__)


class Embedder(Protocol):
    def embed(self, texts: list[str]) -> list[list[float]]: ...


class FastEmbedEmbedder:
    """Lazily loads the ONNX model on first use (downloads ~250 MB once into the cache dir)."""

    def __init__(self, model_name: str, cache_dir: str) -> None:
        self._model_name = model_name
        self._cache_dir = cache_dir
        self._model = None
        self._lock = threading.Lock()

    def _load(self):  # type: ignore[no-untyped-def]
        with self._lock:
            if self._model is None:
                os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
                from fastembed import TextEmbedding  # heavy import, only when needed

                logger.info("Loading embedding model %s", self._model_name)
                self._model = TextEmbedding(self._model_name, cache_dir=self._cache_dir)
        return self._model

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [vector.tolist() for vector in self._load().embed(texts)]


class HashingEmbedder:
    """Deterministic test embedder: each word is hashed into one of 384 buckets, then the vector
    is L2-normalised. Texts sharing words get high cosine similarity; unrelated texts get ~0."""

    def embed(self, texts: list[str]) -> list[list[float]]:
        vectors = []
        for text in texts:
            vector = [0.0] * EMBEDDING_DIM
            for word in re.findall(r"\w+", text.lower()):
                bucket = int(hashlib.md5(word.encode()).hexdigest(), 16) % EMBEDDING_DIM
                vector[bucket] += 1.0
            norm = math.sqrt(sum(v * v for v in vector)) or 1.0
            vectors.append([v / norm for v in vector])
        return vectors


@lru_cache
def get_embedder() -> Embedder:
    settings = get_settings()
    if settings.embedding_backend == "fake":
        return HashingEmbedder()
    return FastEmbedEmbedder(settings.embedding_model, str(settings.embedding_cache_dir))


async def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed off the event loop (model inference is CPU-bound)."""
    return await to_thread.run_sync(get_embedder().embed, texts)


def product_text(product: Product) -> str:
    """The text that represents a product in vector space."""
    return f"{product.title}. {product.description}. Category: {product.category}"
