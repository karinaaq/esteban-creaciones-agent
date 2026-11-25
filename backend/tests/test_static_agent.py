import pytest

from app.adapters.agents.static_agent import StaticReplyAgent
from app.adapters.router.static_messages import GREETING_MESSAGES
from app.domain.chat import ChatTurn


@pytest.mark.asyncio
async def test_static_agent_picks_from_greeting_tuple():
    agent = StaticReplyAgent()
    reply = await agent.handle(ChatTurn(message="Hola", intent="greeting"))
    assert reply.agent == "static"
    assert reply.intent == "greeting"
    assert reply.text in GREETING_MESSAGES
    assert reply.metadata["static"] is True
