from __future__ import annotations

"""向量化模块：把文本转为 embedding。"""

from typing import Iterable

import numpy as np

from hz_bank_rag.core.config import settings
from hz_bank_rag.core.siliconflow_client import SiliconFlowClient, SiliconFlowError
from hz_bank_rag.service.embedding_cache import EmbeddingCache

# 模块级单例缓存，所有 SiliconFlowEmbedder 实例共享。
_global_embedding_cache: EmbeddingCache | None = None


def _get_embedding_cache() -> EmbeddingCache:
    global _global_embedding_cache
    if _global_embedding_cache is None:
        _global_embedding_cache = EmbeddingCache(max_size=settings.embedding_cache_max_size)
    return _global_embedding_cache


class SiliconFlowEmbedder:
    """SiliconFlow 向量生成封装。"""

    def __init__(self, model: str | None = None) -> None:
        self.client = SiliconFlowClient()
        self.model = model or settings.siliconflow_embedding_model
        self._cache = _get_embedding_cache() if settings.enable_embedding_cache else None

    def encode(self, texts: Iterable[str]) -> np.ndarray:
        """将文本集合编码为 `float32` numpy 数组。支持 L1 embedding 缓存。"""
        text_list = list(texts)
        if not text_list:
            return np.zeros((0, 0), dtype=np.float32)

        # L1 缓存：先查缓存，只对未缓存的文本调 API
        if self._cache is not None:
            cached_vectors: dict[int, np.ndarray] = {}
            uncached_texts: list[str] = []
            uncached_indices: list[int] = []
            for i, text in enumerate(text_list):
                cached = self._cache.get(text)
                if cached is not None:
                    cached_vectors[i] = cached
                else:
                    uncached_texts.append(text)
                    uncached_indices.append(i)

            if uncached_texts:
                try:
                    new_vectors = self.client.embeddings(uncached_texts, model=self.model)
                except SiliconFlowError as exc:
                    raise RuntimeError(f"Embedding request failed: {exc}") from exc
                for idx, vec in zip(uncached_indices, new_vectors):
                    vec_np = np.asarray(vec, dtype=np.float32)
                    self._cache.set(text_list[idx], vec_np)
                    cached_vectors[idx] = vec_np

            return np.asarray([cached_vectors[i] for i in range(len(text_list))], dtype=np.float32)

        # 无缓存：直接调 API
        try:
            vectors = self.client.embeddings(text_list, model=self.model)
        except SiliconFlowError as exc:
            raise RuntimeError(f"Embedding request failed: {exc}") from exc

        return np.asarray(vectors, dtype=np.float32)
