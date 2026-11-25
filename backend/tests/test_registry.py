import pytest

from app.adapters.agents.general_agent import GeneralAgent
from app.adapters.agents.registry import AgentRegistry
from app.domain.chat import AgentReply, ChatTurn


class _StubAgent:
    def __init__(self, name: str) -> None:
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    async def handle(self, turn: ChatTurn) -> AgentReply:
        return AgentReply(text=turn.message, intent=self._name, agent=self._name)


def test_registry_resolve_unknown_falls_back():
    registry = AgentRegistry(
        {
            "rag": _StubAgent("rag"),
            "general": GeneralAgent(["general", "rag"]),
        },
        default_intent="general",
    )
    intent, agent = registry.resolve("orders")
    assert intent == "general"
    assert agent.name == "general"


def test_registry_requires_default():
    with pytest.raises(ValueError):
        AgentRegistry({"rag": _StubAgent("rag")}, default_intent="general")
