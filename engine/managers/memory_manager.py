import json
import os
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
import sqlite_vec
from sentence_transformers import SentenceTransformer


@dataclass(frozen=True)
class _NormalizedMessage:
    role: str
    content: str | None
    tool_call_id: str | None
    tool_name: str | None
    arguments_json: str | None
    result: str | None
    error_code: str | None
    error_details: str | None
    embed_text: str | None


class MemoryManager:
    """
    Semantic search over past conversations stored in `sessions/*.json`.

    Stores message metadata in a regular SQLite table and embeddings in a
    `sqlite_vec` vec0 virtual table for nearest-neighbor search.
    """

    def __init__(self):
        self.project_root = Path(__file__).parent.parent.parent
        self.sessions_path = self.project_root / "sessions"

        self.db_path = self.project_root / "workspace" / "memory.db"

        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        embedding_model_name = os.getenv("EMBEDDING_MODEL")
        if not embedding_model_name or not embedding_model_name.strip():
            raise RuntimeError(
                "EMBEDDING_MODEL is not set. Define it in your .env (e.g., EMBEDDING_MODEL=all-MiniLM-L6-v2)."
            )
        hf_token = os.getenv("HF_TOKEN")
        self.embedding_model_name = embedding_model_name

        try:
            self.embedding_model = SentenceTransformer(
                embedding_model_name,
                token=hf_token,
            )
        except Exception as exc:
            raise RuntimeError(
                f"Failed to load embedding model '{embedding_model_name}'. "
                "Ensure EMBEDDING_MODEL is set and dependencies are installed."
            ) from exc

        self.dimensions = int(self.embedding_model.get_embedding_dimension())

        self.connection: sqlite3.Connection | None = None
        self._init_database(dimensions=self.dimensions)
        self.parse_memory()

    def parse_memory(self) -> None:
        """
        Parse `sessions/*.json` and index messages into the sqlite_vec DB.

        This method is incremental: it skips session files that have not changed
        since last indexing (based on file mtime + size).
        """
        if not self.sessions_path.exists():
            return
        assert self.connection is not None

        session_files = sorted(self.sessions_path.glob("*.json"))
        for session_file in session_files:
            try:
                stat = session_file.stat()
            except OSError:
                continue

            source_key = str(session_file.relative_to(self.project_root))
            existing = self.connection.execute(
                "SELECT mtime_ns, size FROM ingestion_state WHERE source_file = ?",
                (source_key,),
            ).fetchone()

            if existing and int(existing[0]) == int(stat.st_mtime_ns) and int(existing[1]) == int(stat.st_size):
                continue

            try:
                raw = session_file.read_text(encoding="utf-8")
                session = json.loads(raw)
            except Exception:
                continue

            session_id = str(session.get("session_id") or "")
            time_initiated = session.get("time_initiated")
            token_count = session.get("token_count")
            messages = session.get("messages") or []
            if not isinstance(messages, list):
                continue

            normalized_messages: list[_NormalizedMessage] = []
            for msg in messages:
                if not isinstance(msg, dict):
                    continue
                normalized_messages.append(self._normalize_message(msg))

            # Embed all texts for this session in a batch
            embed_texts = [m.embed_text for m in normalized_messages if m.embed_text]
            embeddings: np.ndarray | None = None
            if embed_texts:
                embeddings = self._embed_texts(embed_texts)

            now = datetime.utcnow().isoformat(timespec="seconds") + "Z"

            with self.connection:
                # Remove any prior indexing for this session_id
                if session_id:
                    self.connection.execute(
                        "DELETE FROM message_vectors WHERE rowid IN (SELECT id FROM messages WHERE session_id = ?)",
                        (session_id,),
                    )
                    self.connection.execute(
                        "DELETE FROM messages WHERE session_id = ?",
                        (session_id,),
                    )

                embed_i = 0
                for message_index, nm in enumerate(normalized_messages):
                    cur = self.connection.execute(
                        """
                        INSERT INTO messages(
                            session_id,
                            time_initiated,
                            token_count,
                            message_index,
                            role,
                            content,
                            tool_call_id,
                            tool_name,
                            arguments_json,
                            result,
                            error_code,
                            error_details,
                            source_file,
                            indexed_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            session_id,
                            time_initiated,
                            int(token_count) if isinstance(token_count, int) else None,
                            int(message_index),
                            nm.role,
                            nm.content,
                            nm.tool_call_id,
                            nm.tool_name,
                            nm.arguments_json,
                            nm.result,
                            nm.error_code,
                            nm.error_details,
                            source_key,
                            now,
                        ),
                    )
                    message_id = int(cur.lastrowid)

                    if nm.embed_text and embeddings is not None:
                        embedding = embeddings[embed_i]
                        embed_i += 1
                        self.connection.execute(
                            "INSERT INTO message_vectors(rowid, embedding) VALUES (?, vec_f32(?))",
                            (message_id, embedding.astype(np.float32).tobytes()),
                        )

                self.connection.execute(
                    """
                    INSERT INTO ingestion_state(source_file, session_id, mtime_ns, size, indexed_at)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(source_file) DO UPDATE SET
                        session_id=excluded.session_id,
                        mtime_ns=excluded.mtime_ns,
                        size=excluded.size,
                        indexed_at=excluded.indexed_at
                    """,
                    (source_key, session_id, int(stat.st_mtime_ns), int(stat.st_size), now),
                )

    def search_memory(
        self,
        query: str,
        top_k: int = 5,
        *,
        session_id: str | None = None,
        roles: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Semantically search indexed messages.

        Returns a list of dict results ordered by increasing distance.
        """
        if not query or not query.strip() or top_k <= 0:
            return []
        assert self.connection is not None

        query_embedding = self._embed_texts([query])[0]
        query_blob = query_embedding.astype(np.float32).tobytes()

        sql = (
            "SELECT m.*, v.distance AS distance "
            "FROM message_vectors v "
            "JOIN messages m ON m.id = v.rowid "
            "WHERE v.embedding MATCH vec_f32(?) AND v.k = ?"
        )
        params: list[Any] = [query_blob, int(top_k)]

        if session_id:
            sql += " AND m.session_id = ?"
            params.append(session_id)

        if roles:
            roles = [r for r in roles if r]
            if roles:
                placeholders = ",".join(["?"] * len(roles))
                sql += f" AND m.role IN ({placeholders})"
                params.extend(roles)

        sql += " ORDER BY v.distance"

        rows = self.connection.execute(sql, params).fetchall()
        results: list[dict[str, Any]] = []
        for row in rows:
            if isinstance(row, sqlite3.Row):
                results.append(dict(row))
            else:
                # Fallback (should not happen if row_factory is set)
                results.append({"row": row})
        return results

    def _init_database(self, dimensions: int) -> None:
        """Initialize the sqlite DB, load sqlite_vec, and create schema."""
        self.connection = sqlite3.connect(self.db_path)
        self.connection.row_factory = sqlite3.Row

        # Load sqlite_vec extension
        self.connection.enable_load_extension(True)
        sqlite_vec.load(self.connection)
        self.connection.enable_load_extension(False)

        with self.connection:
            self.connection.execute(
                "CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)"
            )
            self.connection.execute(
                """
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    time_initiated TEXT,
                    token_count INTEGER,
                    message_index INTEGER NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT,
                    tool_call_id TEXT,
                    tool_name TEXT,
                    arguments_json TEXT,
                    result TEXT,
                    error_code TEXT,
                    error_details TEXT,
                    source_file TEXT NOT NULL,
                    indexed_at TEXT NOT NULL,
                    UNIQUE(session_id, message_index)
                )
                """
            )

            self.connection.execute(
                """
                CREATE TABLE IF NOT EXISTS ingestion_state (
                    source_file TEXT PRIMARY KEY,
                    session_id TEXT,
                    mtime_ns INTEGER NOT NULL,
                    size INTEGER NOT NULL,
                    indexed_at TEXT NOT NULL
                )
                """
            )

            self.connection.execute(
                f"CREATE VIRTUAL TABLE IF NOT EXISTS message_vectors USING vec0(embedding float[{int(dimensions)}])"
            )

            # Validate or set embedding meta
            existing_model = self._get_meta("embedding_model")
            existing_dim = self._get_meta("embedding_dimensions")

            if existing_model is None and existing_dim is None:
                self._set_meta("embedding_model", self.embedding_model_name)
                self._set_meta("embedding_dimensions", str(int(dimensions)))
            else:
                if existing_model != self.embedding_model_name or existing_dim != str(int(dimensions)):
                    raise RuntimeError(
                        "memory.db embedding configuration mismatch. "
                        f"DB has model={existing_model!r} dim={existing_dim!r}, "
                        f"but config is model={self.embedding_model_name!r} dim={int(dimensions)!r}. "
                        f"Delete {self.db_path} and re-index sessions."
                    )

    def _get_meta(self, key: str) -> str | None:
        assert self.connection is not None
        row = self.connection.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
        if not row:
            return None
        return str(row[0])

    def _set_meta(self, key: str, value: str) -> None:
        assert self.connection is not None
        self.connection.execute(
            "INSERT INTO meta(key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, value),
        )

    def _embed_texts(self, texts: list[str]) -> np.ndarray:
        embeddings = self.embedding_model.encode(
            texts,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        embeddings = np.asarray(embeddings, dtype=np.float32)
        return embeddings

    def _normalize_message(self, msg: dict[str, Any]) -> _NormalizedMessage:
        role = str(msg.get("role") or "").strip() or "unknown"

        # Current harness schema uses `content`.
        content = msg.get("content") if isinstance(msg.get("content"), str) else None

        # Legacy README schema uses `contents: [{type: text, text: ...}, ...]`
        if content is None and isinstance(msg.get("contents"), list):
            parts: list[str] = []
            for part in msg["contents"]:
                if isinstance(part, dict) and part.get("type") == "text" and isinstance(part.get("text"), str):
                    parts.append(part["text"])
            if parts:
                content = "\n".join(parts).strip() or None

        tool_call_id = msg.get("tool_call_id") if isinstance(msg.get("tool_call_id"), str) else None
        tool_name = msg.get("tool_name") if isinstance(msg.get("tool_name"), str) else None
        error_code = msg.get("error_code") if isinstance(msg.get("error_code"), str) else None
        error_details = msg.get("error_details") if isinstance(msg.get("error_details"), str) else None
        result = msg.get("result") if isinstance(msg.get("result"), str) else None

        arguments_json: str | None = None
        raw_args = msg.get("arguments")
        if isinstance(raw_args, str):
            arguments_json = raw_args
        elif isinstance(raw_args, (dict, list)):
            try:
                arguments_json = json.dumps(raw_args, ensure_ascii=False, sort_keys=True)
            except Exception:
                arguments_json = None

        embed_text: str | None = None
        if content and content.strip():
            embed_text = content.strip()
        elif role == "assistant" and tool_name:
            embed_text = f"Tool call: {tool_name}"
            if arguments_json:
                embed_text += f"\nArgs: {arguments_json}"
        elif role == "tool":
            # Embed a compact representation of tool outcomes
            parts: list[str] = []
            if error_code and error_code != "None":
                parts.append(f"Error {error_code}: {error_details or ''}".strip())
            if result and result.strip():
                parts.append(result.strip())
            if parts:
                embed_text = "Tool result: " + "\n".join(parts)

        return _NormalizedMessage(
            role=role,
            content=content,
            tool_call_id=tool_call_id,
            tool_name=tool_name,
            arguments_json=arguments_json,
            result=result,
            error_code=error_code,
            error_details=error_details,
            embed_text=embed_text,
        )
