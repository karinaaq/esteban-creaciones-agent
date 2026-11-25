from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

import pytest

from app.adapters.chat_history.cached_chat_history import CachedChatHistory
from app.domain.chat import ChatRole, StoredChatMessage


@dataclass
class _MemoryHistory:
    sessions: set[str] = field(default_factory=set)
    messages: dict[str, list[StoredChatMessage]] = field(default_factory=dict)
    reads: int = 0

    async def ensure_schema(self) -> None:
        return None

    async def create_session(self) -> str:
        sid = str(uuid4())
        self.sessions.add(sid)
        self.messages[sid] = []
        return sid

    async def session_exists(self, session_id: str) -> bool:
        return session_id in self.sessions

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
        msg = StoredChatMessage(
            id=str(uuid4()),
            role=role,
            content=content,
            intent=intent,
            agent=agent,
            metadata=metadata or {},
            created_at=datetime.now(timezone.utc),
        )
        self.messages.setdefault(session_id, []).append(msg)
        return msg

    async def list_recent(self, session_id: str, *, limit: int) -> list[StoredChatMessage]:
        self.reads += 1
        return list(self.messages.get(session_id, [])[-limit:])


@pytest.mark.asyncio
async def test_cache_avoids_repeated_db_reads():
    inner = _MemoryHistory()
    history = CachedChatHistory(inner, max_cached_sessions=8, keep_per_session=10)
    sid = await history.create_session()
    await history.append(sid, role="user", content="hola")
    await history.append(sid, role="assistant", content="hola!")

    reads_before = inner.reads
    first = await history.list_recent(sid, limit=2)
    assert len(first) == 2
    # create/append no usan list_recent; primera list puede miss si cache incompleta
    # Segunda list con mismo limit debe ser cache hit
    second = await history.list_recent(sid, limit=2)
    assert second == first
    assert inner.reads == reads_before + 1 or inner.reads == reads_before
    # Si la primera ya tenía suficientes msgs en cache tras appends, reads no sube.
    third = await history.list_recent(sid, limit=2)
    assert third == first
    assert inner.reads <= reads_before + 1
