from __future__ import annotations

import hashlib
import json
import pathlib
import uuid
from datetime import datetime, timezone

from hz_bank_rag.core.config import settings
from hz_bank_rag.ingestion.chunker import Chunker
from hz_bank_rag.ingestion.cleaner import clean_text
from hz_bank_rag.ingestion.document_parser import IMAGE_SUFFIXES, parse_document
from hz_bank_rag.ingestion.keywords import extract_chunk_keywords, extract_keywords
from hz_bank_rag.storage.bm25_store import BM25Store
from hz_bank_rag.storage.metadata_store import MetadataStore
from hz_bank_rag.storage.vector_store import BaseVectorStore


class DuplicateDocumentError(RuntimeError):
    """Raised when duplicate documents are detected during ingest."""


class RAGRepository:
    """RAG repository orchestration."""

    def __init__(self, metadata: MetadataStore, vector_store: BaseVectorStore, bm25: BM25Store) -> None:
        self.metadata = metadata
        self.vector_store = vector_store
        self.bm25 = bm25
        self.chunker = Chunker(chunk_size=settings.chunk_size, overlap=settings.chunk_overlap)
        self.bootstrap_indexes()

    def bootstrap_indexes(self) -> None:
        for kb_id in self.metadata.list_kb_ids():
            self._rebuild_bm25(kb_id)

    def ingest_document(self, kb_id: str, file_path: str, parser_type: str = "auto", chunk_strategy: str | None = None) -> dict:
        path = pathlib.Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"file not found: {file_path}")

        resolved_path = str(path.resolve())
        content_hash = self._file_sha256(path)
        file_size = int(path.stat().st_size)
        doc_family_id = self._doc_family_id(path)
        effective_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

        duplicate_hash = self.metadata.get_document_by_kb_and_content_hash(kb_id=kb_id, content_hash=content_hash)
        if duplicate_hash is not None:
            return {
                "kb_id": kb_id,
                "doc_id": duplicate_hash["doc_id"],
                "file_path": duplicate_hash["file_path"],
                "content_hash": content_hash,
                "chunks": len(self.metadata.get_doc_chunk_ids(duplicate_hash["doc_id"])),
                "status": "duplicate_exact",
                "idempotent": True,
                "message": "Exact duplicate detected by content_hash, skipped ingest.",
            }

        self.metadata.ensure_knowledge_base(kb_id=kb_id)

        raw_text = parse_document(str(path))
        cleaned_text = clean_text(raw_text)
        doc_keywords = extract_keywords(cleaned_text)
        near_hash = self._simhash_hex(cleaned_text)
        near_dup = self._detect_near_duplicate(kb_id=kb_id, near_hash=near_hash)
        if near_dup is not None and settings.near_duplicate_reject:
            raise DuplicateDocumentError(
                "near duplicate rejected: "
                f"current={resolved_path}, existing_doc_id={near_dup['doc_id']}, existing_file={near_dup['file_path']}"
            )

        strategy = chunk_strategy or settings.chunk_strategy
        chunks = self.chunker.split(cleaned_text, strategy=strategy)
        chunk_keywords = extract_chunk_keywords(chunks)

        version_no = self.metadata.get_family_max_version(kb_id=kb_id, doc_family_id=doc_family_id) + 1
        self.metadata.deactivate_family_documents(kb_id=kb_id, doc_family_id=doc_family_id)

        doc_id = str(uuid.uuid4())
        self.metadata.add_document(
            doc_id=doc_id,
            kb_id=kb_id,
            file_path=resolved_path,
            parser_type=parser_type,
            file_hash=content_hash,
            content_hash=content_hash,
            near_hash=near_hash,
            file_size=file_size,
            doc_family_id=doc_family_id,
            version_no=version_no,
            effective_at=effective_at,
            is_active=True,
            keywords=doc_keywords,
        )

        source_type = "image" if path.suffix.lower() in IMAGE_SUFFIXES else "text"
        chunk_ids: list[str] = []
        doc_ids: list[str] = []
        for index, chunk_text in enumerate(chunks):
            chunk_id = f"{doc_id}-{index}"
            chunk_ids.append(chunk_id)
            doc_ids.append(doc_id)
            self.metadata.add_chunk(
                chunk_id=chunk_id,
                kb_id=kb_id,
                doc_id=doc_id,
                chunk_index=index,
                text=chunk_text,
                metadata_json=json.dumps(
                    {
                        "file_path": str(path),
                        "file_hash": content_hash,
                        "content_hash": content_hash,
                        "near_hash": near_hash,
                        "file_size": file_size,
                        "file_name": path.name,
                        "file_suffix": path.suffix.lower(),
                        "source_type": source_type,
                        "doc_family_id": doc_family_id,
                        "version_no": version_no,
                        "effective_at": effective_at,
                        "is_active": True,
                        "doc_keywords": doc_keywords,
                        "chunk_keywords": chunk_keywords[index] if index < len(chunk_keywords) else [],
                        "chunk_index": index,
                        "chunk_strategy": strategy,
                    },
                    ensure_ascii=False,
                ),
            )

        self.vector_store.upsert(kb_id=kb_id, chunk_ids=chunk_ids, texts=chunks, doc_ids=doc_ids)
        self._rebuild_bm25(kb_id)
        return {
            "kb_id": kb_id,
            "doc_id": doc_id,
            "file_path": resolved_path,
            "content_hash": content_hash,
            "file_hash": content_hash,
            "near_hash": near_hash,
            "near_duplicate_of": near_dup["doc_id"] if near_dup else "",
            "doc_family_id": doc_family_id,
            "version_no": version_no,
            "effective_at": effective_at,
            "is_active": True,
            "file_size": file_size,
            "doc_keywords": doc_keywords,
            "chunk_strategy": strategy,
            "chunks": len(chunks),
            "status": "ingested",
        }

    def bulk_ingest(self, kb_id: str, file_paths: list[str], chunk_strategy: str | None = None) -> dict:
        results = []
        skipped_duplicates = []
        ingested_count = 0
        for file_path in file_paths:
            try:
                row = self.ingest_document(kb_id=kb_id, file_path=file_path, chunk_strategy=chunk_strategy)
                results.append(row)
                if row.get("status") == "ingested":
                    ingested_count += 1
                else:
                    skipped_duplicates.append(
                        {
                            "file_path": str(pathlib.Path(file_path).resolve()),
                            "reason": row.get("status", "duplicate"),
                            "existing_doc_id": row.get("doc_id", ""),
                        }
                    )
            except DuplicateDocumentError as exc:
                skipped_duplicates.append({"file_path": str(pathlib.Path(file_path).resolve()), "reason": str(exc)})
        return {
            "kb_id": kb_id,
            "documents": results,
            "count": ingested_count,
            "skipped_duplicates": skipped_duplicates,
            "skipped_count": len(skipped_duplicates),
        }

    def delete_document(self, kb_id: str, doc_id: str) -> dict:
        doc = self.metadata.get_document(doc_id)
        chunk_ids = self.metadata.get_doc_chunk_ids(doc_id)
        self.vector_store.delete_chunks(chunk_ids)
        self.metadata.delete_document(doc_id)
        reactivated_doc = ""
        if doc is not None and doc.get("doc_family_id"):
            reactivated_doc = self.metadata.activate_latest_in_family(
                kb_id=kb_id,
                doc_family_id=doc.get("doc_family_id", ""),
            )
        self._rebuild_bm25(kb_id)
        return {
            "kb_id": kb_id,
            "doc_id": doc_id,
            "deleted_chunks": len(chunk_ids),
            "reactivated_doc_id": reactivated_doc,
        }

    def delete_kb(self, kb_id: str) -> dict:
        chunk_rows = self.metadata.get_kb_chunks(kb_id)
        chunk_ids = [row["chunk_id"] for row in chunk_rows]
        self.vector_store.delete_kb(kb_id)
        self.vector_store.delete_chunks(chunk_ids)
        self.metadata.delete_kb(kb_id)
        self.bm25.clear(kb_id)
        return {"kb_id": kb_id, "deleted_chunks": len(chunk_ids)}

    def get_kb_chunk_map(self, kb_id: str, retrieval_scope: str = "active_only") -> dict[str, dict]:
        rows = self.metadata.get_kb_chunks(kb_id, retrieval_scope=retrieval_scope)
        return {row["chunk_id"]: row for row in rows}

    def list_documents(self, kb_id: str | None = None, limit: int = 20) -> list[dict]:
        return self.metadata.list_documents(kb_id=kb_id, limit=limit)

    def get_chunk(self, chunk_id: str) -> dict | None:
        return self.metadata.get_chunk_by_id(chunk_id)

    def get_document(self, doc_id: str) -> dict | None:
        return self.metadata.get_document(doc_id)

    def _rebuild_bm25(self, kb_id: str) -> None:
        chunk_map = self.get_kb_chunk_map(kb_id=kb_id, retrieval_scope="include_history")
        self.bm25.rebuild(kb_id=kb_id, chunk_map={chunk_id: row["text"] for chunk_id, row in chunk_map.items()})

    @staticmethod
    def _file_sha256(path: pathlib.Path) -> str:
        h = hashlib.sha256()
        with path.open("rb") as f:
            while True:
                chunk = f.read(1024 * 1024)
                if not chunk:
                    break
                h.update(chunk)
        return h.hexdigest()

    @staticmethod
    def _doc_family_id(path: pathlib.Path) -> str:
        stem = path.stem.lower().strip()
        stem = "".join(ch if ch.isalnum() or ch in {"_", "-"} else "-" for ch in stem)
        while "--" in stem:
            stem = stem.replace("--", "-")
        for token in ["_v", "-v", "版本", "ver"]:
            if token in stem:
                stem = stem.split(token)[0]
        stem = stem.strip("-_")
        return stem or path.name.lower()

    @staticmethod
    def _simhash_hex(text: str, bits: int = 64) -> str:
        if not text.strip():
            return "0" * (bits // 4)
        vector = [0] * bits
        for token in text.split():
            h = int(hashlib.md5(token.encode("utf-8")).hexdigest(), 16)
            for i in range(bits):
                vector[i] += 1 if (h >> i) & 1 else -1
        fingerprint = 0
        for i, weight in enumerate(vector):
            if weight >= 0:
                fingerprint |= 1 << i
        return f"{fingerprint:0{bits // 4}x}"

    def _detect_near_duplicate(self, kb_id: str, near_hash: str) -> dict | None:
        if not near_hash:
            return None
        candidates = self.metadata.list_document_signatures(kb_id=kb_id, limit=400)
        try:
            current = int(near_hash, 16)
        except ValueError:
            return None
        for doc in candidates:
            existing = doc.get("near_hash", "")
            if not existing:
                continue
            try:
                existing_num = int(existing, 16)
            except ValueError:
                continue
            dist = (current ^ existing_num).bit_count()
            if dist <= settings.near_duplicate_hamming_threshold:
                found = dict(doc)
                found["hamming_distance"] = dist
                return found
        return None
