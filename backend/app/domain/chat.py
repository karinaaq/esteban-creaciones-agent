from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal

ChatRole = Literal["user", "assistant"]


@dataclass(frozen=True, slots=True)
class StoredChatMessage:
    """Mensaje persistido (historial)."""

    role: ChatRole
    content: str
    intent: str | None = None
    agent: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime | None = None
    id: str | None = None


@dataclass(frozen=True, slots=True)
class ChatTurn:
    """Entrada del turno actual al router/agente."""

    message: str
    session_id: str | None = None
    intent: str | None = None
    history: tuple[StoredChatMessage, ...] = ()


@dataclass(frozen=True, slots=True)
class AgentReply:
    """Salida uniforme de cualquier agente."""

    text: str
    intent: str
    agent: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ChatResult:
    """Resultado del use case HandleChat (incluye session_id + historial reciente)."""

    reply: AgentReply
    session_id: str
    history: tuple[StoredChatMessage, ...] = ()



def format_history_for_prompt(messages: tuple[StoredChatMessage, ...] | list[StoredChatMessage]) -> str:
    if not messages:
        return "(sin historial previo)"
    lines: list[str] = []
    for msg in messages:
        label = "Usuario" if msg.role == "user" else "Asistente"
        lines.append(f"{label}: {msg.content}")
    return "\n".join(lines)
