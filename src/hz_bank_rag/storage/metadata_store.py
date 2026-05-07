from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from typing import Any, Iterator

# 元数据存储模块：使用 SQLite 管理知识库、文档、分块、bad case、会话记忆。


class MetadataStore:
    """SQLite 元数据存储。

    作用:
    - 管理知识库/文档/分块
    - 管理 bad case 与会话消息
    - 提供 RAG 检索所需的查询接口
    """

    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        self._init_schema()

    @contextmanager
    def _conn(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.db_path)
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def health(self) -> dict:
        """验证 SQLite 数据库可读写。"""
        try:
            with self._conn() as conn:
                conn.execute("SELECT 1")
            return {"status": "ok", "backend": "sqlite", "path": self.db_path}
        except Exception as exc:
            return {"status": "error", "backend": "sqlite", "detail": str(exc)}

    def _init_schema(self) -> None:
        with self._conn() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS knowledge_bases (
                    kb_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS documents (
                    doc_id TEXT PRIMARY KEY,
                    kb_id TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    file_hash TEXT DEFAULT '',
                    content_hash TEXT DEFAULT '',
                    near_hash TEXT DEFAULT '',
                    file_size INTEGER DEFAULT 0,
                    parser_type TEXT,
                    doc_family_id TEXT DEFAULT '',
                    version_no INTEGER DEFAULT 1,
                    effective_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    is_active INTEGER DEFAULT 1,
                    keywords_json TEXT DEFAULT '[]',
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS chunks (
                    chunk_id TEXT PRIMARY KEY,
                    kb_id TEXT NOT NULL,
                    doc_id TEXT NOT NULL,
                    chunk_index INTEGER NOT NULL,
                    text TEXT NOT NULL,
                    metadata_json TEXT
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS bad_cases (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    kb_id TEXT NOT NULL,
                    query TEXT NOT NULL,
                    rewritten_query TEXT,
                    feedback TEXT NOT NULL,
                    retrieval_snapshot TEXT,
                    category TEXT DEFAULT 'retrieval',
                    severity TEXT DEFAULT 'medium',
                    status TEXT DEFAULT 'open',
                    expected_answer TEXT DEFAULT '',
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS conversation_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    kb_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_conv_session ON conversation_messages(session_id, id)"
            )
            self._ensure_document_columns(conn)
            self._ensure_document_indexes(conn)
            self._ensure_bad_case_columns(conn)

    @staticmethod
    def _ensure_document_columns(conn: sqlite3.Connection) -> None:
        rows = conn.execute("PRAGMA table_info(documents)").fetchall()
        existing = {row[1] for row in rows}
        targets = {
            "file_hash": "ALTER TABLE documents ADD COLUMN file_hash TEXT DEFAULT ''",
            "content_hash": "ALTER TABLE documents ADD COLUMN content_hash TEXT DEFAULT ''",
            "near_hash": "ALTER TABLE documents ADD COLUMN near_hash TEXT DEFAULT ''",
            "file_size": "ALTER TABLE documents ADD COLUMN file_size INTEGER DEFAULT 0",
            "doc_family_id": "ALTER TABLE documents ADD COLUMN doc_family_id TEXT DEFAULT ''",
            "version_no": "ALTER TABLE documents ADD COLUMN version_no INTEGER DEFAULT 1",
            "effective_at": "ALTER TABLE documents ADD COLUMN effective_at TEXT DEFAULT ''",
            "is_active": "ALTER TABLE documents ADD COLUMN is_active INTEGER DEFAULT 1",
            "keywords_json": "ALTER TABLE documents ADD COLUMN keywords_json TEXT DEFAULT '[]'",
        }
        for col, sql in targets.items():
            if col not in existing:
                conn.execute(sql)
        conn.execute("UPDATE documents SET content_hash = file_hash WHERE (content_hash IS NULL OR content_hash = '') AND file_hash != ''")

    @staticmethod
    def _ensure_document_indexes(conn: sqlite3.Connection) -> None:
        conn.execute("CREATE INDEX IF NOT EXISTS idx_docs_kb_path ON documents(kb_id, file_path)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_docs_kb_hash ON documents(kb_id, file_hash)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_docs_kb_content_hash ON documents(kb_id, content_hash)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_docs_kb_family ON documents(kb_id, doc_family_id, version_no)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_docs_kb_active ON documents(kb_id, is_active)")

    @staticmethod
    def _ensure_bad_case_columns(conn: sqlite3.Connection) -> None:
        rows = conn.execute("PRAGMA table_info(bad_cases)").fetchall()
        existing = {row[1] for row in rows}
        targets = {
            "category": "ALTER TABLE bad_cases ADD COLUMN category TEXT DEFAULT 'retrieval'",
            "severity": "ALTER TABLE bad_cases ADD COLUMN severity TEXT DEFAULT 'medium'",
            "status": "ALTER TABLE bad_cases ADD COLUMN status TEXT DEFAULT 'open'",
            "expected_answer": "ALTER TABLE bad_cases ADD COLUMN expected_answer TEXT DEFAULT ''",
        }
        for col, sql in targets.items():
            if col not in existing:
                conn.execute(sql)

    def ensure_knowledge_base(self, kb_id: str, name: str | None = None, description: str | None = None) -> None:
        with self._conn() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO knowledge_bases(kb_id, name, description) VALUES (?, ?, ?)",
                (kb_id, name or kb_id, description or ""),
            )

    def list_kb_ids(self) -> list[str]:
        with self._conn() as conn:
            rows = conn.execute("SELECT kb_id FROM knowledge_bases ORDER BY created_at").fetchall()
        return [row[0] for row in rows]

    def add_document(
        self,
        doc_id: str,
        kb_id: str,
        file_path: str,
        parser_type: str,
        file_hash: str = "",
        content_hash: str = "",
        near_hash: str = "",
        file_size: int = 0,
        doc_family_id: str = "",
        version_no: int = 1,
        effective_at: str = "",
        is_active: bool = True,
        keywords: list[str] | None = None,
    ) -> None:
        keywords_json = json.dumps(keywords or [], ensure_ascii=False)
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO documents("
                "doc_id, kb_id, file_path, file_hash, content_hash, near_hash, file_size, parser_type, "
                "doc_family_id, version_no, effective_at, is_active, keywords_json"
                ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, COALESCE(NULLIF(?, ''), CURRENT_TIMESTAMP), ?, ?)",
                (
                    doc_id,
                    kb_id,
                    file_path,
                    file_hash,
                    content_hash or file_hash,
                    near_hash,
                    int(file_size),
                    parser_type,
                    doc_family_id,
                    int(version_no),
                    effective_at,
                    1 if is_active else 0,
                    keywords_json,
                ),
            )

    def get_document_by_kb_and_path(self, kb_id: str, file_path: str) -> dict[str, Any] | None:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT doc_id, kb_id, file_path, file_hash, content_hash, near_hash, file_size, parser_type, "
                "doc_family_id, version_no, effective_at, is_active, keywords_json, created_at "
                "FROM documents WHERE kb_id = ? AND file_path = ? ORDER BY created_at DESC LIMIT 1",
                (kb_id, file_path),
            ).fetchone()
        if row is None:
            return None
        return self._document_row_to_dict(row)

    def get_document_by_kb_and_hash(self, kb_id: str, file_hash: str) -> dict[str, Any] | None:
        if not file_hash:
            return None
        with self._conn() as conn:
            row = conn.execute(
                "SELECT doc_id, kb_id, file_path, file_hash, content_hash, near_hash, file_size, parser_type, "
                "doc_family_id, version_no, effective_at, is_active, keywords_json, created_at "
                "FROM documents WHERE kb_id = ? AND file_hash = ? ORDER BY created_at DESC LIMIT 1",
                (kb_id, file_hash),
            ).fetchone()
        if row is None:
            return None
        return self._document_row_to_dict(row)

    def get_document_by_kb_and_content_hash(self, kb_id: str, content_hash: str) -> dict[str, Any] | None:
        if not content_hash:
            return None
        with self._conn() as conn:
            row = conn.execute(
                "SELECT doc_id, kb_id, file_path, file_hash, content_hash, near_hash, file_size, parser_type, "
                "doc_family_id, version_no, effective_at, is_active, keywords_json, created_at "
                "FROM documents WHERE kb_id = ? AND content_hash = ? ORDER BY created_at DESC LIMIT 1",
                (kb_id, content_hash),
            ).fetchone()
        if row is None:
            return None
        return self._document_row_to_dict(row)

    def add_chunk(self, chunk_id: str, kb_id: str, doc_id: str, chunk_index: int, text: str, metadata_json: str) -> None:
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO chunks(chunk_id, kb_id, doc_id, chunk_index, text, metadata_json) VALUES (?, ?, ?, ?, ?, ?)",
                (chunk_id, kb_id, doc_id, chunk_index, text, metadata_json),
            )

    def get_kb_chunks(self, kb_id: str, retrieval_scope: str = "active_only") -> list[dict[str, Any]]:
        with self._conn() as conn:
            if retrieval_scope == "include_history":
                rows = conn.execute(
                    "SELECT c.chunk_id, c.doc_id, c.text, c.metadata_json "
                    "FROM chunks c WHERE c.kb_id = ? ORDER BY c.doc_id, c.chunk_index",
                    (kb_id,),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT c.chunk_id, c.doc_id, c.text, c.metadata_json "
                    "FROM chunks c JOIN documents d ON c.doc_id = d.doc_id "
                    "WHERE c.kb_id = ? AND d.is_active = 1 ORDER BY c.doc_id, c.chunk_index",
                    (kb_id,),
                ).fetchall()
        return [
            {
                "chunk_id": row[0],
                "doc_id": row[1],
                "text": row[2],
                "metadata": json.loads(row[3]) if row[3] else {},
            }
            for row in rows
        ]

    def get_chunk_by_id(self, chunk_id: str) -> dict[str, Any] | None:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT chunk_id, kb_id, doc_id, text, metadata_json FROM chunks WHERE chunk_id = ?",
                (chunk_id,),
            ).fetchone()
        if row is None:
            return None
        return {
            "chunk_id": row[0],
            "kb_id": row[1],
            "doc_id": row[2],
            "text": row[3],
            "metadata": json.loads(row[4]) if row[4] else {},
        }

    @staticmethod
    def _document_row_to_dict(row: Any) -> dict[str, Any]:
        keywords = []
        try:
            keywords = json.loads(row[12]) if row[12] else []
        except Exception:
            keywords = []
        return {
            "doc_id": row[0],
            "kb_id": row[1],
            "file_path": row[2],
            "file_hash": row[3] or "",
            "content_hash": row[4] or row[3] or "",
            "near_hash": row[5] or "",
            "file_size": int(row[6] or 0),
            "parser_type": row[7],
            "doc_family_id": row[8] or "",
            "version_no": int(row[9] or 1),
            "effective_at": row[10] or "",
            "is_active": bool(row[11]),
            "keywords": keywords,
            "created_at": row[13],
        }

    def list_documents(self, kb_id: str | None = None, limit: int = 20) -> list[dict[str, Any]]:
        safe_limit = max(1, min(limit, 200))
        with self._conn() as conn:
            if kb_id:
                rows = conn.execute(
                    "SELECT doc_id, kb_id, file_path, file_hash, content_hash, near_hash, file_size, parser_type, "
                    "doc_family_id, version_no, effective_at, is_active, keywords_json, created_at "
                    "FROM documents WHERE kb_id = ? ORDER BY created_at DESC LIMIT ?",
                    (kb_id, safe_limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT doc_id, kb_id, file_path, file_hash, content_hash, near_hash, file_size, parser_type, "
                    "doc_family_id, version_no, effective_at, is_active, keywords_json, created_at "
                    "FROM documents ORDER BY created_at DESC LIMIT ?",
                    (safe_limit,),
                ).fetchall()
        return [self._document_row_to_dict(row) for row in rows]

    def get_doc_chunk_ids(self, doc_id: str) -> list[str]:
        with self._conn() as conn:
            rows = conn.execute("SELECT chunk_id FROM chunks WHERE doc_id = ?", (doc_id,)).fetchall()
        return [row[0] for row in rows]

    def get_document(self, doc_id: str) -> dict[str, Any] | None:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT doc_id, kb_id, file_path, file_hash, content_hash, near_hash, file_size, parser_type, "
                "doc_family_id, version_no, effective_at, is_active, keywords_json, created_at "
                "FROM documents WHERE doc_id = ?",
                (doc_id,),
            ).fetchone()
        if row is None:
            return None
        return self._document_row_to_dict(row)

    def delete_document(self, doc_id: str) -> None:
        with self._conn() as conn:
            conn.execute("DELETE FROM chunks WHERE doc_id = ?", (doc_id,))
            conn.execute("DELETE FROM documents WHERE doc_id = ?", (doc_id,))

    def get_family_max_version(self, kb_id: str, doc_family_id: str) -> int:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT COALESCE(MAX(version_no), 0) FROM documents WHERE kb_id = ? AND doc_family_id = ?",
                (kb_id, doc_family_id),
            ).fetchone()
        return int(row[0] or 0)

    def deactivate_family_documents(self, kb_id: str, doc_family_id: str) -> int:
        with self._conn() as conn:
            cur = conn.execute(
                "UPDATE documents SET is_active = 0 WHERE kb_id = ? AND doc_family_id = ? AND is_active = 1",
                (kb_id, doc_family_id),
            )
        return int(cur.rowcount or 0)

    def activate_latest_in_family(self, kb_id: str, doc_family_id: str) -> str:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT doc_id FROM documents WHERE kb_id = ? AND doc_family_id = ? "
                "ORDER BY version_no DESC, created_at DESC LIMIT 1",
                (kb_id, doc_family_id),
            ).fetchone()
            if row is None:
                return ""
            doc_id = row[0]
            conn.execute(
                "UPDATE documents SET is_active = CASE WHEN doc_id = ? THEN 1 ELSE 0 END "
                "WHERE kb_id = ? AND doc_family_id = ?",
                (doc_id, kb_id, doc_family_id),
            )
        return doc_id

    def list_document_signatures(self, kb_id: str, limit: int = 200) -> list[dict[str, Any]]:
        safe_limit = max(1, min(limit, 1000))
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT doc_id, kb_id, file_path, file_hash, content_hash, near_hash, file_size, parser_type, "
                "doc_family_id, version_no, effective_at, is_active, keywords_json, created_at "
                "FROM documents WHERE kb_id = ? ORDER BY created_at DESC LIMIT ?",
                (kb_id, safe_limit),
            ).fetchall()
        return [self._document_row_to_dict(row) for row in rows if row[5] or row[4]]

    def delete_kb(self, kb_id: str) -> None:
        with self._conn() as conn:
            conn.execute("DELETE FROM chunks WHERE kb_id = ?", (kb_id,))
            conn.execute("DELETE FROM documents WHERE kb_id = ?", (kb_id,))
            conn.execute("DELETE FROM bad_cases WHERE kb_id = ?", (kb_id,))
            conn.execute("DELETE FROM conversation_messages WHERE kb_id = ?", (kb_id,))
            conn.execute("DELETE FROM knowledge_bases WHERE kb_id = ?", (kb_id,))

    def add_bad_case(
        self,
        kb_id: str,
        query: str,
        rewritten_query: str,
        feedback: str,
        retrieval_snapshot: str = "",
        category: str = "retrieval",
        severity: str = "medium",
        status: str = "open",
        expected_answer: str = "",
    ) -> None:
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO bad_cases(kb_id, query, rewritten_query, feedback, retrieval_snapshot, category, severity, status, expected_answer) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (kb_id, query, rewritten_query, feedback, retrieval_snapshot, category, severity, status, expected_answer),
            )

    def list_bad_cases(self, kb_id: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
        safe_limit = max(1, min(limit, 500))
        with self._conn() as conn:
            if kb_id:
                rows = conn.execute(
                    "SELECT id, kb_id, query, rewritten_query, feedback, retrieval_snapshot, category, severity, status, expected_answer, created_at "
                    "FROM bad_cases WHERE kb_id = ? ORDER BY id DESC LIMIT ?",
                    (kb_id, safe_limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT id, kb_id, query, rewritten_query, feedback, retrieval_snapshot, category, severity, status, expected_answer, created_at "
                    "FROM bad_cases ORDER BY id DESC LIMIT ?",
                    (safe_limit,),
                ).fetchall()

        results = []
        for row in rows:
            snapshot = {}
            try:
                snapshot = json.loads(row[5]) if row[5] else {}
            except Exception:
                snapshot = {"raw": row[5]}
            results.append(
                {
                    "id": row[0],
                    "kb_id": row[1],
                    "query": row[2],
                    "rewritten_query": row[3],
                    "feedback": row[4],
                    "retrieval_snapshot": snapshot,
                    "category": row[6],
                    "severity": row[7],
                    "status": row[8],
                    "expected_answer": row[9],
                    "created_at": row[10],
                }
            )
        return results

    def list_bad_case_for_ragas(self, kb_id: str, limit: int = 50) -> list[dict[str, Any]]:
        rows = self.list_bad_cases(kb_id=kb_id, limit=limit)
        data = []
        for row in rows:
            snapshot = row.get("retrieval_snapshot", {}) or {}
            contexts = [hit.get("preview_text", "") for hit in snapshot.get("top_hits", []) if isinstance(hit, dict)]
            expected = row.get("expected_answer", "")
            if not expected:
                continue
            data.append(
                {
                    "question": row.get("query", ""),
                    "answer": "",
                    "contexts": contexts,
                    "ground_truth": expected,
                    "bad_case_id": row.get("id"),
                }
            )
        return data

    def add_conversation_message(self, session_id: str, kb_id: str, role: str, content: str) -> None:
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO conversation_messages(session_id, kb_id, role, content) VALUES (?, ?, ?, ?)",
                (session_id, kb_id, role, content),
            )

    def get_conversation_messages(self, session_id: str, kb_id: str, limit: int = 40) -> list[dict[str, Any]]:
        safe_limit = max(1, min(limit, 200))
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT id, role, content, created_at FROM conversation_messages "
                "WHERE session_id = ? AND kb_id = ? ORDER BY id DESC LIMIT ?",
                (session_id, kb_id, safe_limit),
            ).fetchall()
        rows.reverse()
        return [
            {"id": row[0], "role": row[1], "content": row[2], "created_at": row[3]}
            for row in rows
        ]

    def delete_conversation_messages_before(self, session_id: str, kb_id: str, max_keep: int) -> int:
        keep = max(1, max_keep)
        with self._conn() as conn:
            ids = conn.execute(
                "SELECT id FROM conversation_messages WHERE session_id = ? AND kb_id = ? ORDER BY id DESC LIMIT ?",
                (session_id, kb_id, keep),
            ).fetchall()
            if not ids:
                return 0
            min_keep_id = min([row[0] for row in ids])
            cur = conn.execute(
                "DELETE FROM conversation_messages WHERE session_id = ? AND kb_id = ? AND id < ?",
                (session_id, kb_id, min_keep_id),
            )
            return int(cur.rowcount or 0)
