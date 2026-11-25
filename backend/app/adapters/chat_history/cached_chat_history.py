from __future__ import annotations

from collections import OrderedDict, deque
from typing import Any

from app.domain.chat import ChatRole, StoredChatMessage
from app.ports.chat_history import ChatHistoryPort


class CachedChatHistory:
    """
    Write-through cache en memoria delante de Postgres.

    - Escritura: DB + cache de esa sesión.
    - Lectura: cache hit → 0 queries; miss → SELECT ... LIMIT N y rellena cache.
    - Solo guarda las últimas `keep_per_session` msgs por sesión (acotado).
    - Eviction LRU de sesiones cuando supera `max_cached_sessions`.
    """

    def __init__(
        self,
        inner: ChatHistoryPort,
        *,
        max_cached_sessions: int = 256,
        keep_per_session: int = 20,
    ) -> None:
        self._inner = inner
        self._max_cached_sessions = max_cached_sessions
        self._keep_per_session = keep_per_session
        self._cache: OrderedDict[str, deque[StoredChatMessage]] = OrderedDict()

    async def ensure_schema(self) -> None:
        await self._inner.ensure_schema()

    async def create_session(self) -> str:
        session_id = await self._inner.create_session()
        self._put(session_id, deque(maxlen=self._keep_per_session))
        return session_id

    async def session_exists(self, session_id: str) -> bool:
        if session_id in self._cache:
            self._cache.move_to_end(session_id)
            return True
        return await self._inner.session_exists(session_id)

    async def append(
        self,
        session_id: str,
        *,
        role: ChatRole,
        content: str,
        intent: str | None = None,
        agent: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> StoredChatMessage:
        stored = await self._inner.append(
            session_id,
            role=role,
            content=content,
            intent=intent,
            agent=agent,
            metadata=metadata,
        )
        bucket = self._cache.get(session_id)
        if bucket is None:
            # Si no estaba en cache, no precargamos todo: solo arrancamos con este msg.
            bucket = deque(maxlen=self._keep_per_session)
            self._put(session_id, bucket)
        else:
            self._cache.move_to_end(session_id)
        bucket.append(stored)
        return stored

    async def list_recent(
        self,
        session_id: str,
        *,
        limit: int,
    ) -> list[StoredChatMessage]:
        if limit <= 0:
            return []

        cached = self._cache.get(session_id)
        if cached is not None and len(cached) >= limit:
            self._cache.move_to_end(session_id)
            return list(cached)[-limit:]

        # Miss o cache incompleto: una sola query LIMIT (barata)
        fetch_limit = max(limit, self._keep_per_session)
        loaded = await self._inner.list_recent(session_id, limit=fetch_limit)
        bucket = deque(loaded, maxlen=self._keep_per_session)
        self._put(session_id, bucket)
        return list(bucket)[-limit:]

    def _put(self, session_id: str, bucket: deque[StoredChatMessage]) -> None:
        self._cache[session_id] = bucket
        self._cache.move_to_end(session_id)
        while len(self._cache) > self._max_cached_sessions:
            self._cache.popitem(last=False)
