from __future__ import annotations

from typing import Protocol

from app.domain.chat import AgentReply, ChatTurn


class AgentPort(Protocol):
    """
    Contrato de un agente del chatbot.

    Para agregar uno nuevo:
    1. Implementá esta interfaz
    2. Registrate en el AgentRegistry (composition root)
    3. Enseñale al Router a devolver ese intent
    """

    @property
    def name(self) -> str:
        """Identificador estable, ej. 'rag', 'orders'."""
        ...

    async def handle(self, turn: ChatTurn) -> AgentReply:
        ...
