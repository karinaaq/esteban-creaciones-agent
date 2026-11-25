from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

import pytest

from app.adapters.agents.registry import AgentRegistry
from app.adapters.guardrails.noop_guardrails import NoopGuardrails
from app.domain.chat import AgentReply, ChatRole, ChatTurn, StoredChatMessage
from app.domain.routing import RouteDecision
from app.use_cases.handle_chat import HandleChat


@dataclass
class _MemoryHistory:
    sessions: set[str] = field(default_factory=set)
    messages: dict[str, list[StoredChatMessage]] = field(default_factory=dict)

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
        return list(self.messages.get(session_id, [])[-limit:])


class _Router:
    async def route(self, turn: ChatTurn) -> RouteDecision:
        # Exponer cuánta history recibió
        self.last_history_len = len(turn.history)
        return RouteDecision(intent="general", source="static")


class _StaticAgent:
    name = "static"

    async def handle(self, turn: ChatTurn) -> AgentReply:
        self.last_history_len = len(turn.history)
        return AgentReply(text="ok", intent="general", agent=self.name, metadata={})


@pytest.mark.asyncio
async def test_handle_chat_windows_and_persists():
    history = _MemoryHistory()
    router = _Router()
    agent = _StaticAgent()
    registry = AgentRegistry({"general": agent}, default_intent="general")
    chat = HandleChat(
        router=router,
        registry=registry,
        history=history,
        guardrails=NoopGuardrails(),
        history_window=6,
        router_history_window=2,
    )

    first = await chat.execute("hola")
    assert first.session_id
    assert len(history.messages[first.session_id]) == 2  # user + assistant
    assert len(first.history) == 2
    assert first.history[-1].role == "assistant"
    assert router.last_history_len == 0

    second = await chat.execute("cuanto tarda?", session_id=first.session_id)
    assert second.session_id == first.session_id
    assert router.last_history_len == 2
    assert agent.last_history_len == 2
    assert len(history.messages[first.session_id]) == 4
    assert len(second.history) == 4
    assert second.history[-2].content == "cuanto tarda?"

