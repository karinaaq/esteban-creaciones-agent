from __future__ import annotations

import json
import uuid
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.domain.chat import ChatRole, StoredChatMessage


class PostgresChatHistory:
    """Fuente de verdad del historial. Lecturas siempre con LIMIT."""

    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine
        self._sessions = async_sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )

    async def ensure_schema(self) -> None:
        async with self._engine.begin() as conn:
            await conn.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS chat_sessions (
                        id UUID PRIMARY KEY,
                        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                    )
                    """
                )
            )
            await conn.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS chat_messages (
                        id UUID PRIMARY KEY,
                        session_id UUID NOT NULL
                            REFERENCES chat_sessions(id) ON DELETE CASCADE,
                        role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
                        content TEXT NOT NULL,
                        intent TEXT NULL,
                        agent TEXT NULL,
                        metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
                        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                    )
                    """
                )
            )
            await conn.execute(
                text(
                    """
                    CREATE INDEX IF NOT EXISTS chat_messages_session_created_idx
                    ON chat_messages (session_id, created_at DESC)
                    """
                )
            )

    async def create_session(self) -> str:
        session_id = str(uuid.uuid4())
        async with self._sessions() as session:
            async with session.begin():
                await session.execute(
                    text("INSERT INTO chat_sessions (id) VALUES (:id)"),
                    {"id": session_id},
                )
        return session_id

    async def session_exists(self, session_id: str) -> bool:
        async with self._sessions() as session:
            result = await session.execute(
                text("SELECT 1 FROM chat_sessions WHERE id = :id"),
                {"id": session_id},
            )
            return result.first() is not None

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
        message_id = str(uuid.uuid4())
        payload = metadata or {}
        async with self._sessions() as session:
            async with session.begin():
                await session.execute(
                    text(
                        """
                        INSERT INTO chat_messages (
                            id, session_id, role, content, intent, agent, metadata
                        ) VALUES (
                            :id, :session_id, :role, :content, :intent, :agent,
                            CAST(:metadata AS jsonb)
                        )
                        """
                    ),
                    {
                        "id": message_id,
                        "session_id": session_id,
                        "role": role,
                        "content": content,
                        "intent": intent,
                        "agent": agent,
                        "metadata": json.dumps(payload),
                    },
                )
                await session.execute(
                    text(
                        """
                        UPDATE chat_sessions
                        SET updated_at = NOW()
                        WHERE id = :session_id
                        """
                    ),
                    {"session_id": session_id},
                )
                row = await session.execute(
                    text(
                        """
                        SELECT created_at
                        FROM chat_messages
                        WHERE id = :id
                        """
                    ),
                    {"id": message_id},
                )
                created_at = row.scalar_one()

        return StoredChatMessage(
            id=message_id,
            role=role,
            content=content,
            intent=intent,
            agent=agent,
            metadata=payload,
            created_at=created_at,
        )

    async def list_recent(
        self,
        session_id: str,
        *,
        limit: int,
    ) -> list[StoredChatMessage]:
        if limit <= 0:
            return []
        async with self._sessions() as session:
            result = await session.execute(
                text(
                    """
                    SELECT id, role, content, intent, agent, metadata, created_at
                    FROM chat_messages
                    WHERE session_id = :session_id
                    ORDER BY created_at DESC
                    LIMIT :limit
                    """
                ),
                {"session_id": session_id, "limit": limit},
            )
            rows = list(result.mappings().all())

        messages: list[StoredChatMessage] = []
        for row in reversed(rows):  # cronológico ascendente
            metadata = row["metadata"]
            if isinstance(metadata, str):
                metadata = json.loads(metadata)
            messages.append(
                StoredChatMessage(
                    id=str(row["id"]),
                    role=row["role"],
                    content=row["content"],
                    intent=row["intent"],
                    agent=row["agent"],
                    metadata=dict(metadata or {}),
                    created_at=row["created_at"],
                )
            )
        return messages
