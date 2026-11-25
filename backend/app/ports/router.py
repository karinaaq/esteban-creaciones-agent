from __future__ import annotations

from typing import Protocol

from app.domain.chat import ChatTurn
from app.domain.routing import RouteDecision


class RouterPort(Protocol):
    """Clasifica el mensaje; puede informar source y usage de tokens."""

    async def route(self, turn: ChatTurn) -> RouteDecision:
        ...
