from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import uuid4

import pytest

from app.adapters.agents.orders_agent import OrdersAgent
from app.adapters.prompts.yaml_prompt_repository import YamlPromptRepository
from app.domain.chat import ChatTurn
from app.domain.llm import LlmCompletion, LlmInferenceConfig, LlmUsage
from app.domain.orders import OrderRequest


@dataclass
class _MemoryOrders:
    rows: dict[str, OrderRequest] = field(default_factory=dict)

    async def ensure_schema(self) -> None:
        return None

    async def get_or_create_draft(self, session_id: str) -> OrderRequest:
        for row in self.rows.values():
            if row.session_id == session_id and row.status == "draft":
                return row
        order = OrderRequest(
            id=str(uuid4()),
            session_id=session_id,
            item_description=None,
            desired_when=None,
            contact_phone=None,
            status="draft",
            requested_at=datetime.now(timezone.utc),
        )
        self.rows[order.id] = order
        return order

    async def save(self, order: OrderRequest) -> OrderRequest:
        self.rows[order.id] = order
        return order

    async def get(self, order_id: str) -> OrderRequest | None:
        return self.rows.get(order_id)


class _FakeLlm:
    provider_name = "fake"
    model_name = "fake"

    def __init__(self, payload: str) -> None:
        self._payload = payload

    async def complete(self, *, system: str, user: str, config: LlmInferenceConfig):
        return LlmCompletion(
            text=self._payload,
            usage=LlmUsage(input_tokens=1, output_tokens=1),
            provider=self.provider_name,
            model=self.model_name,
        )


@pytest.mark.asyncio
async def test_orders_agent_asks_for_missing():
    store = _MemoryOrders()
    agent = OrdersAgent(
        llm=_FakeLlm(
            '{"item_description":"centro de mesa","desired_when":null,'
            '"contact_phone":null,"assistant_message":"¿Para qué fecha lo necesitás?",'
            '"complete":false}'
        ),
        prompts=YamlPromptRepository(),
        orders=store,
    )
    sid = str(uuid4())
    reply = await agent.handle(
        ChatTurn(message="Quiero encargar un centro de mesa", session_id=sid)
    )
    assert reply.intent == "orders"
    assert reply.metadata["status"] == "draft"
    assert reply.metadata["collected"]["item_description"] == "COMPLETADO"
    assert reply.metadata["collected"]["desired_when"] == "NO_COMPLETADO"
    assert "fecha" in reply.text.lower() or "cuando" in reply.text.lower() or "cuándo" in reply.text.lower()


@pytest.mark.asyncio
async def test_orders_agent_submits_when_complete():
    store = _MemoryOrders()
    draft = await store.get_or_create_draft(str(uuid4()))
    draft = draft.with_updates(
        item_description="disfraz",
        desired_when="15 de diciembre",
    )
    await store.save(draft)

    agent = OrdersAgent(
        llm=_FakeLlm(
            '{"item_description":null,"desired_when":null,'
            '"contact_phone":"0981123456",'
            '"assistant_message":"Perfecto, quedó registrado.",'
            '"complete":true}'
        ),
        prompts=YamlPromptRepository(),
        orders=store,
    )
    reply = await agent.handle(
        ChatTurn(message="Mi número es 0981123456", session_id=draft.session_id)
    )
    assert reply.metadata["status"] == "submitted"
    lower = reply.text.lower()
    assert "comunic" in lower
    assert "pulir" in lower or "empezar" in lower
    saved = await store.get(draft.id)
    assert saved is not None
    assert saved.status == "submitted"
    assert saved.contact_phone == "0981123456"
