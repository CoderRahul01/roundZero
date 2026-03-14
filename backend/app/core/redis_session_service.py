"""
RedisSessionService — production-grade ADK session service backed by Upstash Redis.

Design rationale:
- Only session STATE is persisted in Redis; events are kept in-memory for the
  duration of a single WebSocket connection. Gemini's session_resumption config
  handles audio-context reconnection at the API level, so we don't need to
  replay events from Redis.
- append_event writes to Redis only when state_delta is non-empty, avoiding
  hundreds of expensive HTTP calls for audio-chunk events (which carry no state).
- All Redis calls are wrapped in asyncio.to_thread to keep the async event loop
  unblocked (Upstash REST client is synchronous under the hood).

Redis key schema:
  adk:session:{app_name}:{user_id}:{session_id}   → JSON blob (state + metadata)
  adk:idx:{app_name}:{user_id}                    → JSON list of session IDs
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any

from google.adk.events import Event
from google.adk.sessions import Session, _session_util
from google.adk.sessions.base_session_service import (
    BaseSessionService,
    GetSessionConfig,
    ListSessionsResponse,
)
from google.adk.sessions.state import State

from app.core.redis_client import get_redis

logger = logging.getLogger(__name__)

_SESSION_TTL = 7200  # 2 hours


def _session_key(app_name: str, user_id: str, session_id: str) -> str:
    return f"adk:session:{app_name}:{user_id}:{session_id}"


def _index_key(app_name: str, user_id: str) -> str:
    return f"adk:idx:{app_name}:{user_id}"


def _serialize(app_name: str, user_id: str, session: Session) -> str:
    return json.dumps(
        {
            "id": session.id,
            "app_name": app_name,
            "user_id": user_id,
            "state": session.state,
            "last_update_time": session.last_update_time,
        }
    )


def _deserialize(raw: str) -> Session:
    data = json.loads(raw)
    return Session(
        id=data["id"],
        app_name=data["app_name"],
        user_id=data["user_id"],
        state=data.get("state", {}),
        events=[],  # Events are transient; not stored in Redis
        last_update_time=data.get("last_update_time", 0.0),
    )


async def _redis_get(key: str) -> str | None:
    redis = get_redis()
    if not redis:
        return None
    return await asyncio.to_thread(redis.get, key)


async def _redis_set(key: str, value: str, ttl: int = _SESSION_TTL) -> None:
    redis = get_redis()
    if not redis:
        return
    await asyncio.to_thread(redis.setex, key, ttl, value)


async def _redis_delete(key: str) -> None:
    redis = get_redis()
    if not redis:
        return
    await asyncio.to_thread(redis.delete, key)


class RedisSessionService(BaseSessionService):
    """Production ADK session service that persists session state in Upstash Redis."""

    async def create_session(
        self,
        *,
        app_name: str,
        user_id: str,
        state: dict[str, Any] | None = None,
        session_id: str | None = None,
    ) -> Session:
        import uuid

        if not session_id:
            session_id = str(uuid.uuid4())

        # Extract only session-scoped state (ignore app/user prefixes for now)
        state_deltas = _session_util.extract_state_delta(state or {})
        session_state = state_deltas.get("session", {})

        session = Session(
            id=session_id,
            app_name=app_name,
            user_id=user_id,
            state=session_state,
            events=[],
            last_update_time=time.time(),
        )

        key = _session_key(app_name, user_id, session_id)
        await _redis_set(key, _serialize(app_name, user_id, session))

        # Maintain a session index per user
        await self._add_to_index(app_name, user_id, session_id)

        logger.info(f"RedisSessionService: created session {session_id}")
        return session

    async def get_session(
        self,
        *,
        app_name: str,
        user_id: str,
        session_id: str,
        config: GetSessionConfig | None = None,
    ) -> Session | None:
        key = _session_key(app_name, user_id, session_id)
        raw = await _redis_get(key)
        if not raw:
            return None
        try:
            session = _deserialize(raw)
            return session
        except Exception as e:
            logger.error(f"RedisSessionService: failed to deserialize session {session_id}: {e}")
            return None

    async def list_sessions(self, *, app_name: str, user_id: str | None = None) -> ListSessionsResponse:
        # Return lightweight session stubs (no events/state per ADK contract)
        if not user_id:
            return ListSessionsResponse(sessions=[])

        raw_index = await _redis_get(_index_key(app_name, user_id))
        if not raw_index:
            return ListSessionsResponse(sessions=[])

        session_ids: list[str] = json.loads(raw_index)
        sessions = []
        for sid in session_ids:
            raw = await _redis_get(_session_key(app_name, user_id, sid))
            if raw:
                try:
                    sessions.append(_deserialize(raw))
                except Exception:
                    pass

        return ListSessionsResponse(sessions=sessions)

    async def delete_session(self, *, app_name: str, user_id: str, session_id: str) -> None:
        await _redis_delete(_session_key(app_name, user_id, session_id))
        await self._remove_from_index(app_name, user_id, session_id)
        logger.info(f"RedisSessionService: deleted session {session_id}")

    async def append_event(self, session: Session, event: Event) -> Event:
        # Let the base class update in-memory session state from state_delta
        event = await super().append_event(session=session, event=event)

        # Only write to Redis when state actually changed (skips audio-chunk events)
        has_state_delta = (
            event.actions
            and event.actions.state_delta
            and any(not k.startswith(State.TEMP_PREFIX) for k in event.actions.state_delta)
        )
        if has_state_delta:
            key = _session_key(session.app_name, session.user_id, session.id)
            try:
                await _redis_set(key, _serialize(session.app_name, session.user_id, session))
            except Exception as e:
                logger.error(f"RedisSessionService: failed to persist state for {session.id}: {e}")

        return event

    # ------------------------------------------------------------------ #
    # Private helpers                                                       #
    # ------------------------------------------------------------------ #

    async def _add_to_index(self, app_name: str, user_id: str, session_id: str) -> None:
        key = _index_key(app_name, user_id)
        try:
            raw = await _redis_get(key)
            ids: list[str] = json.loads(raw) if raw else []
            if session_id not in ids:
                ids.append(session_id)
            await _redis_set(key, json.dumps(ids))
        except Exception as e:
            logger.warning(f"RedisSessionService: failed to update index: {e}")

    async def _remove_from_index(self, app_name: str, user_id: str, session_id: str) -> None:
        key = _index_key(app_name, user_id)
        try:
            raw = await _redis_get(key)
            ids: list[str] = json.loads(raw) if raw else []
            ids = [i for i in ids if i != session_id]
            await _redis_set(key, json.dumps(ids))
        except Exception as e:
            logger.warning(f"RedisSessionService: failed to update index: {e}")
