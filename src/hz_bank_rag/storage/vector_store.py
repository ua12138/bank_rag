from __future__ import annotations

import logging
import re
from abc import ABC, abstractmethod
from typing import Any

import numpy as np

from hz_bank_rag.core.config import milvus_fields, settings
from hz_bank_rag.retrieval.embedding import SiliconFlowEmbedder

try:
    from pymilvus import DataType, Function, FunctionType, MilvusClient
except Exception:  # pragma: no cover
    DataType = None
    Function = None
    FunctionType = None
    MilvusClient = None

logger = logging.getLogger(__name__)


def _slug(value: str, max_len: int = 24) -> str:
    text = re.sub(r"[^a-zA-Z0-9]+", "_", value).strip("_").lower()
    if not text:
        text = "model"
    return text[:max_len]


class BaseVectorStore(ABC):
    """Base interface for vector stores."""

    def __init__(self, dim: int = 1024) -> None:
        self.dim = dim
        self.embedder = SiliconFlowEmbedder()

    @abstractmethod
    def upsert(self, kb_id: str, chunk_ids: list[str], texts: list[str], doc_ids: list[str]) -> None:
        raise NotImplementedError

    @abstractmethod
    def delete_chunks(self, chunk_ids: list[str]) -> None:
        raise NotImplementedError

    @abstractmethod
    def delete_kb(self, kb_id: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def search(self, query: str, kb_id: str, top_k: int = 5) -> list[tuple[str, float]]:
        raise NotImplementedError

    def search_sparse(self, query: str, kb_id: str, top_k: int = 5) -> list[tuple[str, float]]:
        return []

    def get_collection_policy(self) -> dict[str, Any]:
        return {"provider": self.__class__.__name__, "managed": False}

    def list_managed_collections(self) -> list[str]:
        return []

    def cleanup_collections(self, dry_run: bool = True) -> dict[str, Any]:
        return {
            "provider": self.__class__.__name__,
            "dry_run": dry_run,
            "cleaned": [],
            "skipped": [],
            "note": "Collection lifecycle is not supported for this vector store.",
        }


class InMemoryVectorStore(BaseVectorStore):
    """Fallback in-memory vector store."""

    def __init__(self, dim: int = 1024) -> None:
        super().__init__(dim=dim)
        self._vectors: dict[str, np.ndarray] = {}
        self._chunk_to_kb: dict[str, str] = {}

    def upsert(self, kb_id: str, chunk_ids: list[str], texts: list[str], doc_ids: list[str]) -> None:
        vectors = self.embedder.encode(texts)
        if vectors.size == 0:
            return
        self.dim = int(vectors.shape[1])
        for idx, chunk_id in enumerate(chunk_ids):
            self._vectors[chunk_id] = vectors[idx]
            self._chunk_to_kb[chunk_id] = kb_id

    def delete_chunks(self, chunk_ids: list[str]) -> None:
        for chunk_id in chunk_ids:
            self._vectors.pop(chunk_id, None)
            self._chunk_to_kb.pop(chunk_id, None)

    def delete_kb(self, kb_id: str) -> None:
        delete_ids = [chunk_id for chunk_id, value in self._chunk_to_kb.items() if value == kb_id]
        self.delete_chunks(delete_ids)

    def search(self, query: str, kb_id: str, top_k: int = 5) -> list[tuple[str, float]]:
        query_vector = self.embedder.encode([query])
        if query_vector.size == 0:
            return []
        q = query_vector[0]

        scored: list[tuple[str, float]] = []
        for chunk_id, vector in self._vectors.items():
            if self._chunk_to_kb.get(chunk_id) != kb_id:
                continue
            score = float(np.dot(q, vector))
            scored.append((chunk_id, score))
        scored.sort(key=lambda item: item[1], reverse=True)
        return scored[:top_k]


class MilvusVectorStore(BaseVectorStore):
    """Milvus store with dense + BM25 sparse retrieval, and dense-only fallback."""

    def __init__(
        self,
        uri: str,
        dim: int = 1024,
        token: str | None = None,
        collection_name: str = "hz_bank_rag_chunks",
        consistency_level: str = "Strong",
        enable_dynamic_field: bool = True,
    ) -> None:
        super().__init__(dim=dim)
        self.uri = uri
        self.token = token
        self.base_collection_name = collection_name
        self.consistency_level = consistency_level
        self.enable_dynamic_field = enable_dynamic_field
        self.embedding_model_slug = _slug(settings.siliconflow_embedding_model)
        self.collection_mode = "hbm25"
        self.collection_name = self._build_collection_name(self.dim, mode=self.collection_mode)
        self.legacy_collection_name = self._build_collection_name(self.dim, mode="legacy")

        self._fallback = InMemoryVectorStore(dim=dim)
        self.client = None
        self.available = False
        self.sparse_available = False
        self._connect()

    def _build_collection_name(self, dim: int, mode: str) -> str:
        base = f"{self.base_collection_name}__{self.embedding_model_slug}__d{dim}"
        if mode == "legacy":
            return base
        return f"{base}__{mode}"

    def _managed_prefix(self) -> str:
        return f"{self.base_collection_name}__"

    def _connect(self) -> None:
        if MilvusClient is None or Function is None or FunctionType is None:
            logger.warning("pymilvus BM25 capability is unavailable. Falling back to InMemoryVectorStore.")
            return
        try:
            self.client = MilvusClient(uri=self.uri, token=self.token)
            self._ensure_collection()
            self.available = True
        except Exception as exc:  # pragma: no cover
            logger.warning("Milvus connection failed. Falling back to InMemoryVectorStore: %s", exc)
            self.available = False
            self.sparse_available = False
            self.client = None

    def _ensure_collection(self) -> None:
        if self.client is None:
            return

        if self.client.has_collection(collection_name=self.collection_name):
            self.client.load_collection(collection_name=self.collection_name)
            self.sparse_available = self._collection_supports_sparse(self.collection_name)
            return

        self._create_collection_with_hybrid_schema(collection_name=self.collection_name)
        self.client.load_collection(collection_name=self.collection_name)
        self.sparse_available = self._collection_supports_sparse(self.collection_name)

        if self.client.has_collection(collection_name=self.legacy_collection_name):
            self._migrate_legacy_dense_collection()

    def _create_collection_with_hybrid_schema(self, collection_name: str) -> None:
        if self.client is None:
            return

        if self.client.has_collection(collection_name=collection_name):
            return

        try:
            schema = self.client.create_schema(auto_id=False, enable_dynamic_field=self.enable_dynamic_field)
            schema.add_field(field_name=milvus_fields.primary_key, datatype=DataType.VARCHAR, max_length=128, is_primary=True)
            schema.add_field(field_name=milvus_fields.kb_id, datatype=DataType.VARCHAR, max_length=128)
            schema.add_field(field_name=milvus_fields.doc_id, datatype=DataType.VARCHAR, max_length=128)
            schema.add_field(field_name=milvus_fields.text, datatype=DataType.VARCHAR, max_length=8192, enable_analyzer=True)
            schema.add_field(field_name=milvus_fields.vector, datatype=DataType.FLOAT_VECTOR, dim=self.dim)
            schema.add_field(field_name=milvus_fields.sparse_vector, datatype=DataType.SPARSE_FLOAT_VECTOR)
            schema.add_function(
                Function(
                    name=milvus_fields.bm25_function,
                    function_type=FunctionType.BM25,
                    input_field_names=[milvus_fields.text],
                    output_field_names=[milvus_fields.sparse_vector],
                )
            )

            index_params = self.client.prepare_index_params()
            index_params.add_index(field_name=milvus_fields.vector, index_type="AUTOINDEX", metric_type="COSINE")
            index_params.add_index(
                field_name=milvus_fields.sparse_vector,
                index_type="SPARSE_INVERTED_INDEX",
                metric_type="BM25",
            )
            self.client.create_collection(
                collection_name=collection_name,
                schema=schema,
                index_params=index_params,
                consistency_level=self.consistency_level,
            )
            return
        except Exception as exc:
            logger.warning("Create hybrid Milvus collection failed. Fallback to dense-only schema: %s", exc)

        # Dense-only fallback: service remains available even when sparse/BM25 capability fails.
        schema = self.client.create_schema(auto_id=False, enable_dynamic_field=self.enable_dynamic_field)
        schema.add_field(field_name=milvus_fields.primary_key, datatype=DataType.VARCHAR, max_length=128, is_primary=True)
        schema.add_field(field_name=milvus_fields.kb_id, datatype=DataType.VARCHAR, max_length=128)
        schema.add_field(field_name=milvus_fields.doc_id, datatype=DataType.VARCHAR, max_length=128)
        schema.add_field(field_name=milvus_fields.text, datatype=DataType.VARCHAR, max_length=8192)
        schema.add_field(field_name=milvus_fields.vector, datatype=DataType.FLOAT_VECTOR, dim=self.dim)

        index_params = self.client.prepare_index_params()
        index_params.add_index(field_name=milvus_fields.vector, index_type="AUTOINDEX", metric_type="COSINE")
        self.client.create_collection(
            collection_name=collection_name,
            schema=schema,
            index_params=index_params,
            consistency_level=self.consistency_level,
        )

    def _collection_supports_sparse(self, collection_name: str) -> bool:
        if self.client is None:
            return False
        try:
            desc = self.client.describe_collection(collection_name=collection_name)
        except Exception:
            return False

        fields = desc.get("fields", [])
        functions = desc.get("functions", [])
        has_sparse_field = any(field.get("name") == milvus_fields.sparse_vector for field in fields)
        has_bm25_function = any(fn.get("name") == milvus_fields.bm25_function for fn in functions)
        return bool(has_sparse_field and has_bm25_function)

    def _migrate_legacy_dense_collection(self) -> None:
        if self.client is None:
            return
        if not self.client.has_collection(collection_name=self.legacy_collection_name):
            return

        try:
            stats = self.client.get_collection_stats(collection_name=self.collection_name)
            num_entities = int(stats.get("row_count", stats.get("num_entities", 0)))
        except Exception:
            num_entities = 0
        if num_entities > 0:
            return

        logger.warning(
            "Migrating legacy dense collection '%s' into '%s'.",
            self.legacy_collection_name,
            self.collection_name,
        )
        it = self.client.query_iterator(
            collection_name=self.legacy_collection_name,
            batch_size=1000,
            limit=-1,
            filter="",
            output_fields=[
                milvus_fields.primary_key,
                milvus_fields.kb_id,
                milvus_fields.doc_id,
                milvus_fields.text,
                milvus_fields.vector,
            ],
        )
        try:
            while True:
                rows = it.next()
                if not rows:
                    break
                self.client.insert(collection_name=self.collection_name, data=rows)
        finally:
            it.close()

    def _sync_dim_with_vectors(self, vectors: np.ndarray) -> None:
        vector_dim = int(vectors.shape[1])
        if vector_dim == self.dim:
            return

        old_dim = self.dim
        old = self.collection_name
        self.dim = vector_dim
        self._fallback.dim = vector_dim
        self.collection_name = self._build_collection_name(self.dim, mode=self.collection_mode)
        self.legacy_collection_name = self._build_collection_name(self.dim, mode="legacy")
        logger.warning(
            "Embedding dimension changed from %s to %s. Active collection switched from '%s' to '%s'.",
            old_dim,
            self.dim,
            old,
            self.collection_name,
        )
        self._ensure_collection()

    def upsert(self, kb_id: str, chunk_ids: list[str], texts: list[str], doc_ids: list[str]) -> None:
        self._fallback.upsert(kb_id=kb_id, chunk_ids=chunk_ids, texts=texts, doc_ids=doc_ids)

        if not self.available or self.client is None:
            return

        vectors = self.embedder.encode(texts)
        if vectors.size == 0:
            return

        self._sync_dim_with_vectors(vectors)

        rows = []
        for idx, chunk_id in enumerate(chunk_ids):
            rows.append(
                {
                    milvus_fields.primary_key: chunk_id,
                    milvus_fields.kb_id: kb_id,
                    milvus_fields.doc_id: doc_ids[idx],
                    milvus_fields.text: texts[idx][:8192],
                    milvus_fields.vector: vectors[idx].tolist(),
                }
            )

        self.delete_chunks(chunk_ids)
        self.client.insert(collection_name=self.collection_name, data=rows)

    def delete_chunks(self, chunk_ids: list[str]) -> None:
        self._fallback.delete_chunks(chunk_ids)
        if not chunk_ids or not self.available or self.client is None:
            return
        quoted = ", ".join([f'"{chunk_id}"' for chunk_id in chunk_ids])
        self.client.delete(collection_name=self.collection_name, filter=f'{milvus_fields.primary_key} in [{quoted}]')

    def delete_kb(self, kb_id: str) -> None:
        self._fallback.delete_kb(kb_id)
        if not self.available or self.client is None:
            return
        self.client.delete(collection_name=self.collection_name, filter=f'{milvus_fields.kb_id} == "{kb_id}"')

    def search(self, query: str, kb_id: str, top_k: int = 5) -> list[tuple[str, float]]:
        local_hits = self._fallback.search(query=query, kb_id=kb_id, top_k=top_k)
        if not self.available or self.client is None:
            return local_hits

        query_vec = self.embedder.encode([query])
        if query_vec.size == 0:
            return local_hits

        self._sync_dim_with_vectors(query_vec)
        query_vector = query_vec[0].tolist()

        result = self.client.search(
            collection_name=self.collection_name,
            data=[query_vector],
            anns_field=milvus_fields.vector,
            filter=f'{milvus_fields.kb_id} == "{kb_id}"',
            limit=top_k,
            output_fields=[milvus_fields.primary_key],
            search_params={"metric_type": "COSINE", "params": {}},
        )

        hits = []
        for row in result[0]:
            entity = row.get("entity", {})
            chunk_id = entity.get(milvus_fields.primary_key) or row.get(milvus_fields.primary_key)
            score = float(row.get("distance", row.get("score", 0.0)))
            if chunk_id is None:
                continue
            hits.append((chunk_id, score))
        return hits or local_hits

    def search_sparse(self, query: str, kb_id: str, top_k: int = 5) -> list[tuple[str, float]]:
        if not self.available or self.client is None or not self.sparse_available:
            return []
        if not query.strip():
            return []

        try:
            result = self.client.search(
                collection_name=self.collection_name,
                data=[query],
                anns_field=milvus_fields.sparse_vector,
                filter=f'{milvus_fields.kb_id} == "{kb_id}"',
                limit=top_k,
                output_fields=[milvus_fields.primary_key],
                search_params={"metric_type": "BM25", "params": {}},
            )
        except Exception as exc:
            logger.warning("Milvus sparse BM25 search failed, fallback to in-memory BM25: %s", exc)
            self.sparse_available = False
            return []

        hits = []
        for row in result[0]:
            entity = row.get("entity", {})
            chunk_id = entity.get(milvus_fields.primary_key) or row.get(milvus_fields.primary_key)
            score = float(row.get("distance", row.get("score", 0.0)))
            if chunk_id is None:
                continue
            hits.append((chunk_id, score))
        return hits

    def get_collection_policy(self) -> dict[str, Any]:
        return {
            "provider": "Milvus",
            "managed": True,
            "base_collection": self.base_collection_name,
            "embedding_model_slug": self.embedding_model_slug,
            "active_collection": self.collection_name,
            "legacy_collection": self.legacy_collection_name,
            "sparse_available": self.sparse_available,
            "naming_rule": "<base>__<embedding_model_slug>__d<dim>__hbm25",
            "lifecycle": {
                "archive": "logical archive (snapshot metadata report)",
                "cleanup": "drop stale managed collections after review",
            },
        }

    def list_managed_collections(self) -> list[str]:
        if not self.available or self.client is None:
            return []
        try:
            names = self.client.list_collections()
        except Exception:
            return []
        prefix = self._managed_prefix()
        return sorted([name for name in names if name.startswith(prefix)])

    def cleanup_collections(self, dry_run: bool = True) -> dict[str, Any]:
        managed = self.list_managed_collections()
        stale = [name for name in managed if name != self.collection_name]
        cleaned: list[str] = []

        if not dry_run and self.available and self.client is not None:
            for name in stale:
                try:
                    self.client.drop_collection(collection_name=name)
                    cleaned.append(name)
                except Exception as exc:  # pragma: no cover
                    logger.warning("Failed to drop stale collection '%s': %s", name, exc)

        return {
            "provider": "Milvus",
            "dry_run": dry_run,
            "active_collection": self.collection_name,
            "managed_collections": managed,
            "stale_collections": stale,
            "cleaned": cleaned,
        }
