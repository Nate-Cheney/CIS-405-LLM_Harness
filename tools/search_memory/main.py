from __future__ import annotations

from typing import Any

from agent_framework import tool


_mm = None


def _truncate(text: str | None, limit: int) -> str | None:
    if text is None:
        return None
    text = str(text)
    if limit <= 0:
        return "" if text else ""
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 1)] + "…"


def _normalize_roles(roles: Any) -> list[str] | None:
    if roles is None:
        return None
    if isinstance(roles, str):
        raw = [roles]
    elif isinstance(roles, list):
        raw = roles
    else:
        return None

    allowed = {"user", "assistant", "tool"}
    normalized: list[str] = []
    for role in raw:
        if not isinstance(role, str):
            continue
        role_norm = role.strip().lower()
        if role_norm in allowed:
            normalized.append(role_norm)

    return normalized or None


@tool
def search_memory(
    query: str,
    top_k: int = 5,
    session_id: str | None = None,
    roles: list[str] | None = None,
    refresh: bool = True,
    preview_chars: int = 240,
) -> dict[str, Any]:
    """
    Semantically search indexed conversation history.

    This tool searches prior session messages stored in `sessions/*.json`, indexed
    by `engine/managers/memory_manager.py` into `workspace/memory.db` using
    embeddings + nearest-neighbor search.

    Args:
        query: Natural language search query.
        top_k: Number of results to return (clamped to 1..20).
        session_id: Optional session id to restrict the search.
        roles: Optional role filter (subset of ["user", "assistant", "tool"]).
        refresh: If true, re-parse `sessions/*.json` before searching.
        preview_chars: Max characters to return for content/result previews.

    Returns:
        A JSON-serializable dict with keys: query, top_k, filters, results, error.
    """

    effective_query = "" if query is None else str(query)
    effective_query = effective_query.strip()

    try:
        effective_top_k = int(top_k)
    except Exception:
        effective_top_k = 5
    effective_top_k = max(1, min(20, effective_top_k))

    effective_session_id = None
    if isinstance(session_id, str) and session_id.strip():
        effective_session_id = session_id.strip()

    effective_roles = _normalize_roles(roles)

    try:
        effective_preview_chars = int(preview_chars)
    except Exception:
        effective_preview_chars = 240
    effective_preview_chars = max(0, min(2000, effective_preview_chars))

    response: dict[str, Any] = {
        "query": effective_query,
        "top_k": effective_top_k,
        "filters": {
            "session_id": effective_session_id,
            "roles": effective_roles,
        },
        "results": [],
        "error": None,
    }

    if not effective_query:
        response["results"] = []
        response["error"] = "Query is empty."
        return response

    global _mm
    try:
        if _mm is None:
            from managers.memory_manager import MemoryManager

            _mm = MemoryManager()

        if refresh:
            _mm.parse_memory()

        rows = _mm.search_memory(
            effective_query,
            effective_top_k,
            session_id=effective_session_id,
            roles=effective_roles,
        )

        results: list[dict[str, Any]] = []
        for row in rows:
            # row is a dict produced by MemoryManager.search_memory()
            content_preview = _truncate(row.get("content"), effective_preview_chars)
            result_preview = _truncate(row.get("result"), effective_preview_chars)

            distance_val = row.get("distance")
            try:
                distance_val = float(distance_val)
            except Exception:
                distance_val = None

            results.append(
                {
                    "distance": distance_val,
                    "session_id": row.get("session_id"),
                    "time_initiated": row.get("time_initiated"),
                    "message_index": row.get("message_index"),
                    "role": row.get("role"),
                    "content_preview": content_preview,
                    "tool_name": row.get("tool_name"),
                    "arguments_json": row.get("arguments_json"),
                    "result_preview": result_preview,
                    "error_code": row.get("error_code"),
                    "error_details": row.get("error_details"),
                    "source_file": row.get("source_file"),
                    "indexed_at": row.get("indexed_at"),
                }
            )

        response["results"] = results
        return response

    except Exception as exc:
        response["results"] = []
        response["error"] = str(exc)
        return response
