from __future__ import annotations

from app.ports.agent import AgentPort


class AgentRegistry:
    """Mapa intent → agente. Agregar un agente = una línea en el composition root."""

    def __init__(
        self,
        agents: dict[str, AgentPort],
        *,
        default_intent: str = "general",
    ) -> None:
        if default_intent not in agents:
            raise ValueError(f"default_intent '{default_intent}' not in agents")
        self._agents = agents
        self._default_intent = default_intent

    @property
    def intents(self) -> list[str]:
        return sorted(self._agents.keys())

    def get(self, intent: str) -> AgentPort:
        return self._agents.get(intent, self._agents[self._default_intent])

    def resolve(self, intent: str) -> tuple[str, AgentPort]:
        if intent in self._agents:
            return intent, self._agents[intent]
        return self._default_intent, self._agents[self._default_intent]
