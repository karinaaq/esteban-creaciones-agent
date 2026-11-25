from __future__ import annotations

from typing import Any, Protocol

from app.domain.chat import ChatRole, StoredChatMessage


class ChatHistoryPort(Protocol):
    """
    Persistencia + lectura reciente del historial.

    Importante para performance:
    - Siempre listar con LIMIT (nunca traer la conversación entera).
    - El adapter cacheado evita ir a Postgres en sesiones calientes.
    """

    async def ensure_schema(self) -> None: ...

    async def create_session(self) -> str: ...

    async def session_exists(self, session_id: str) -> bool: ...

    async def append(
        self,
        session_id: str,
        *,
        role: ChatRole,
        content: str,
        intent: str | None = None,
        agent: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> StoredChatMessage: ...

    async def list_recent(
        self,
        session_id: str,
        *,
        limit: int,
    ) -> list[StoredChatMessage]: ...
