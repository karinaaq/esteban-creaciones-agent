from __future__ import annotations

import random

from app.adapters.router.static_messages import MESSAGES_BY_INTENT
from app.domain.chat import AgentReply, ChatTurn


class StaticReplyAgent:
    """
    Responde con mensajes fijos (tuplas editables en static_messages.py).
    No llama LLM ni RAG.
    """

    def __init__(self, *, default_intent: str = "general") -> None:
        self._default_intent = default_intent

    @property
    def name(self) -> str:
        return "static"

    async def handle(self, turn: ChatTurn) -> AgentReply:
        intent = turn.intent or self._default_intent
        options = MESSAGES_BY_INTENT.get(intent) or MESSAGES_BY_INTENT[self._default_intent]
        text = random.choice(options)
        return AgentReply(
            text=text,
            intent=intent,
            agent=self.name,
            metadata={"static": True, "variants": len(options)},
        )
