"""
SessionService
==============
Handles interview session state across two stores:

  Redis (primary)
    - session_config:{id}       → JSON blob with role/topics/questions/user_profile
    - session_results:{id}      → Redis list; each element is a JSON-encoded
                                  question result.  RPUSH is atomic — safe under
                                  concurrent writes during an interview.

  Neon PostgreSQL (durable fallback)
    - sessions table            → one row per interview
    - question_results table    → one row per scored question

ReportGenerator reads from Redis first (fast, hot path) and falls back to
Neon only when Redis data is absent (e.g., after key expiry).
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional

from app.core.redis_client import get_redis
from app.core.settings import get_settings

logger = logging.getLogger(__name__)

# Redis key TTLs
_SESSION_CONFIG_TTL = 3_600   # 1 hour
_SESSION_RESULTS_TTL = 7_200  # 2 hours — long enough to cover report generation


def _results_key(session_id: str) -> str:
    return f"session_results:{session_id}"


def _config_key(session_id: str) -> str:
    return f"session_config:{session_id}"


class SessionService:
    # ------------------------------------------------------------------
    # Session config helpers (role, topics, questions, user_profile …)
    # ------------------------------------------------------------------

    @staticmethod
    async def get_session(session_id: str) -> Dict[str, Any]:
        """Retrieve the session configuration blob from Redis."""
        redis = get_redis()
        if not redis:
            logger.warning("Redis unavailable — returning empty session config")
            return {}
        try:
            raw = await asyncio.to_thread(redis.get, _config_key(session_id))
            if raw:
                return json.loads(raw)
        except Exception as exc:
            logger.error(f"get_session({session_id}): Redis read failed: {exc}")
        return {}

    @staticmethod
    async def save_session(
        session_id: str,
        data: Dict[str, Any],
        expire: int = _SESSION_CONFIG_TTL,
    ) -> None:
        """Persist the session configuration blob to Redis."""
        redis = get_redis()
        if not redis:
            return
        try:
            await asyncio.to_thread(
                redis.setex, _config_key(session_id), expire, json.dumps(data)
            )
        except Exception as exc:
            logger.error(f"save_session({session_id}): Redis write failed: {exc}")

    @staticmethod
    async def update_current_question(
        session_id: str, index: int, text: str
    ) -> None:
        """Update the active question pointer inside the session config blob."""
        data = await SessionService.get_session(session_id)
        if data:
            data["current_question_index"] = index
            data["current_question_text"] = text
            await SessionService.save_session(session_id, data)

    # ------------------------------------------------------------------
    # Question-result persistence  (the hot path for scoring)
    # ------------------------------------------------------------------

    @staticmethod
    async def append_question_result(
        session_id: str,
        result: Dict[str, Any],
    ) -> None:
        """
        Atomically append a scored question result to the session's result list.

        Uses Redis RPUSH — atomic, no read-modify-write, safe under concurrent
        calls (follow-ups, rapid answers).  Also persists to Neon as a durable
        backup; Neon failures are logged but never bubble up to the caller.
        """
        # --- Primary: Redis atomic list append ---
        redis = get_redis()
        if redis:
            try:
                key = _results_key(session_id)
                payload = json.dumps(result)
                await asyncio.to_thread(redis.rpush, key, payload)
                await asyncio.to_thread(redis.expire, key, _SESSION_RESULTS_TTL)
                logger.debug(
                    f"append_question_result: RPUSH ok for session {session_id} "
                    f"Q{result.get('question_number')}"
                )
            except Exception as exc:
                logger.error(
                    f"append_question_result: Redis RPUSH failed for {session_id}: {exc}"
                )

        # --- Secondary: Neon durable storage (best-effort) ---
        settings = get_settings()
        if not settings.database_url:
            return

        try:
            import asyncpg  # type: ignore

            conn = await asyncpg.connect(settings.database_url)
            try:
                # Ensure the session row exists before inserting the FK-dependent
                # question_results row.  We need a minimal user_profiles row too.
                user_id = result.get("user_id") or "anonymous"
                await conn.execute(
                    """
                    INSERT INTO user_profiles (id, created_at, updated_at)
                    VALUES ($1, now(), now())
                    ON CONFLICT (id) DO NOTHING
                    """,
                    user_id,
                )
                await conn.execute(
                    """
                    INSERT INTO sessions (id, user_id, created_at)
                    VALUES ($1, $2, now())
                    ON CONFLICT (id) DO NOTHING
                    """,
                    session_id,
                    user_id,
                )
                await conn.execute(
                    """
                    INSERT INTO question_results (
                        session_id, question_number, question_text,
                        user_answer, ideal_answer, score, max_score,
                        feedback, filler_word_count, emotion_log, created_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, now())
                    """,
                    session_id,
                    result.get("question_number"),
                    result.get("question_text") or "",
                    result.get("user_answer") or "",
                    result.get("ideal_answer") or "",
                    int(result["score"]) if result.get("score") is not None else 0,
                    int(result.get("max_score") or 10),
                    result.get("feedback") or "",
                    int(result.get("filler_word_count") or 0),
                    # Pass dict directly — asyncpg serialises JSONB natively
                    result.get("emotion_log") or {},
                )
            finally:
                await conn.close()
        except Exception as exc:
            # Non-fatal: Redis already holds the data.
            logger.warning(
                f"append_question_result: Neon write failed for {session_id} "
                f"(Redis copy is safe): {exc}"
            )

    @staticmethod
    async def get_session_results(session_id: str) -> List[Dict[str, Any]]:
        """
        Return all scored question results for a session.

        Resolution order:
          1. Redis list  (session_results:{id})  — fastest, most complete
          2. Redis config blob (results key)     — legacy fallback
          3. Neon PostgreSQL                     — durable fallback after Redis expiry
        """
        # 1. Redis list (primary hot path)
        redis = get_redis()
        if redis:
            try:
                key = _results_key(session_id)
                raw_list = await asyncio.to_thread(redis.lrange, key, 0, -1)
                if raw_list:
                    return [json.loads(item) for item in raw_list]
            except Exception as exc:
                logger.error(
                    f"get_session_results: Redis LRANGE failed for {session_id}: {exc}"
                )

            # 2. Legacy session-config blob (written by old code path)
            try:
                data = await SessionService.get_session(session_id)
                if data and data.get("results"):
                    logger.info(
                        f"get_session_results: falling back to config blob for {session_id}"
                    )
                    return data["results"]
            except Exception as exc:
                logger.error(
                    f"get_session_results: config blob fallback failed for {session_id}: {exc}"
                )

        # 3. Neon (cold fallback — Redis key may have expired)
        settings = get_settings()
        if not settings.database_url:
            return []

        try:
            import asyncpg  # type: ignore

            conn = await asyncpg.connect(settings.database_url)
            try:
                rows = await conn.fetch(
                    """
                    SELECT
                        question_number, question_text, user_answer,
                        ideal_answer, score, max_score, feedback,
                        filler_word_count, emotion_log
                    FROM question_results
                    WHERE session_id = $1
                    ORDER BY created_at ASC
                    """,
                    session_id,
                )
                if rows:
                    logger.info(
                        f"get_session_results: loaded {len(rows)} rows from Neon "
                        f"for {session_id}"
                    )
                    return [dict(r) for r in rows]
            finally:
                await conn.close()
        except Exception as exc:
            logger.error(
                f"get_session_results: Neon fallback failed for {session_id}: {exc}"
            )

        return []

    # ------------------------------------------------------------------
    # Neon session lifecycle helpers
    # ------------------------------------------------------------------

    @staticmethod
    async def create_session_neon(
        session_id: str, data: Dict[str, Any]
    ) -> None:
        """Insert a minimal session record into Neon (best-effort)."""
        settings = get_settings()
        if not settings.database_url:
            return

        try:
            import asyncpg  # type: ignore

            conn = await asyncpg.connect(settings.database_url)
            try:
                user_id = data.get("user_id") or "anonymous"
                # Ensure the user_profiles FK target exists first
                await conn.execute(
                    """
                    INSERT INTO user_profiles (id, created_at, updated_at)
                    VALUES ($1, now(), now())
                    ON CONFLICT (id) DO NOTHING
                    """,
                    user_id,
                )
                await conn.execute(
                    """
                    INSERT INTO sessions (id, user_id, role, topics, difficulty, mode, created_at)
                    VALUES ($1, $2, $3, $4, $5, $6, now())
                    ON CONFLICT (id) DO NOTHING
                    """,
                    session_id,
                    user_id,
                    data.get("role"),
                    data.get("topics"),
                    data.get("difficulty"),
                    data.get("mode"),
                )
            finally:
                await conn.close()
        except Exception as exc:
            logger.error(f"create_session_neon({session_id}): {exc}")

    @staticmethod
    async def create_audit_log(
        event_type: str,
        user_id: str,
        session_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Write an audit log entry to Neon (best-effort)."""
        settings = get_settings()
        if not settings.database_url:
            return

        try:
            import asyncpg  # type: ignore

            conn = await asyncpg.connect(settings.database_url)
            try:
                await conn.execute(
                    """
                    INSERT INTO audit_logs (event_type, user_id, session_id, metadata, created_at)
                    VALUES ($1, $2, $3, $4, now())
                    """,
                    event_type,
                    user_id,
                    session_id,
                    json.dumps(metadata or {}),
                )
            finally:
                await conn.close()
        except Exception as exc:
            logger.error(f"create_audit_log({event_type}): {exc}")

    # ------------------------------------------------------------------
    # Legacy shim — kept so existing callers (websocket.py old path) don't break
    # ------------------------------------------------------------------

    @staticmethod
    async def save_question_result(
        session_id: str,
        result: Dict[str, Any],
    ) -> bool:
        """
        Deprecated shim — delegates to append_question_result.
        Kept for backward compatibility with any call sites not yet migrated.
        """
        try:
            await SessionService.append_question_result(session_id, result)
            return True
        except Exception:
            return False
