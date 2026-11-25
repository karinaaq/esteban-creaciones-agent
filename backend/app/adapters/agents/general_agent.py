from __future__ import annotations

from app.domain.chat import AgentReply, ChatTurn


class GeneralAgent:
    """Fallback: saludos / fuera de alcance. No usa RAG ni LLM."""

    def __init__(self, available_intents: list[str]) -> None:
        self._available = available_intents

    @property
    def name(self) -> str:
        return "general"

    async def handle(self, turn: ChatTurn) -> AgentReply:
        text = turn.message.strip().lower()
        if any(g in text for g in ("hola", "buenas", "buenos", "hey")):
            reply = (
                "Hola, soy el asistente de Esteban Creaciones. "
                "Puedo ayudarte con preguntas frecuentes (plazos, productos, "
                "precios orientativos, entrega)."
            )
        elif "gracias" in text:
            reply = "¡Con gusto! Si tenés otra consulta sobre productos o plazos, escribile."
        else:
            reply = (
                "Por ahora puedo atender consultas de tipo FAQ (rag). "
                "Preguntame por plazos, productos, precios orientativos o entrega. "
                f"Intents disponibles: {', '.join(self._available)}."
            )
        return AgentReply(
            text=reply,
            intent="general",
            agent=self.name,
            metadata={},
        )
