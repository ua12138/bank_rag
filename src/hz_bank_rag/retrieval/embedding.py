from __future__ import annotations

from typing import Iterable

import numpy as np

from hz_bank_rag.core.config import settings
from hz_bank_rag.core.siliconflow_client import SiliconFlowClient, SiliconFlowError


class SiliconFlowEmbedder:
    """Embedding wrapper backed by SiliconFlow API."""

    def __init__(self, model: str | None = None) -> None:
        self.client = SiliconFlowClient()
        self.model = model or settings.siliconflow_embedding_model

    def encode(self, texts: Iterable[str]) -> np.ndarray:
        text_list = [text for text in texts]
        if not text_list:
            return np.zeros((0, 0), dtype=np.float32)

        try:
            vectors = self.client.embeddings(text_list, model=self.model)
        except SiliconFlowError as exc:
            raise RuntimeError(f"Embedding request failed: {exc}") from exc

        return np.asarray(vectors, dtype=np.float32)
