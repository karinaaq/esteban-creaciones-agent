from __future__ import annotations

import uuid
from dataclasses import dataclass, replace

from app.adapters.agents.registry import AgentRegistry
from app.domain.chat import AgentReply, ChatResult, ChatTurn
from app.observability import (
    get_tracer,
    record_chat,
    record_guardrail_block,
    set_span_error,
    set_span_io,
)
from app.ports.chat_history import ChatHistoryPort
from app.ports.guardrails import GuardrailsPort
from app.ports.router import RouterPort


@dataclass(slots=True)
class HandleChat:
    """
    Orquesta guardrail input → historial → router → agente → historial.
    """

    router: RouterPort
    registry: AgentRegistry
    history: ChatHistoryPort
    guardrails: GuardrailsPort
    history_window: int = 6
    router_history_window: int = 2

    async def execute(self, message: str, *, session_id: str | None = None) -> ChatResult:
        tracer = get_tracer()
        with tracer.start_as_current_span("chat.handle") as span:
            try:
                return await self._execute(message, session_id=session_id, span=span)
            except Exception as exc:
                set_span_error(span, exc)
                raise

    async def _execute(
        self,
        message: str,
        *,
        session_id: str | None,
        span,
    ) -> ChatResult:
        sid = await self._resolve_session(session_id)
        span.set_attribute("chat.session_id", sid)
        span.set_attribute("chat.message_chars", len(message or ""))
        set_span_io(span, input=message)

        input_gate = await self.guardrails.check_input(message)
        if not input_gate.allowed:
            span.set_attribute("chat.blocked", True)
            span.set_attribute("guardrail.code", input_gate.code or "")
            span.set_attribute("guardrail.verdict", input_gate.verdict)
            record_guardrail_block(code=input_gate.code or "unknown")
            record_chat(intent="blocked", agent="guardrail", generated=False)

            blocked = AgentReply(
                text=input_gate.message,
                intent="blocked",
                agent="guardrail",
                metadata={
                    "guardrail": {
                        "verdict": input_gate.verdict,
                        "code": input_gate.code,
                        "details": input_gate.details,
                    },
                    "generated": False,
                },
            )
            set_span_io(span, output=blocked.text)
            await self.history.append(sid, role="user", content=message)
            await self.history.append(
                sid,
                role="assistant",
                content=blocked.text,
                intent=blocked.intent,
                agent=blocked.agent,
                metadata=blocked.metadata,
            )
            recent = await self.history.list_recent(
                sid, limit=self.history_window + 2
            )
            return ChatResult(
                reply=blocked,
                session_id=sid,
                history=tuple(recent),
            )

        fetch_n = max(self.history_window, self.router_history_window)
        prior = await self.history.list_recent(sid, limit=fetch_n)

        await self.history.append(sid, role="user", content=message)

        router_history = tuple(prior[-self.router_history_window :]) if prior else ()
        agent_history = tuple(prior[-self.history_window :]) if prior else ()

        turn = ChatTurn(
            message=message,
            session_id=sid,
            history=router_history,
        )
        decision = await self.router.route(turn)
        resolved_intent, agent = self.registry.resolve(decision.intent)

        span.set_attribute("chat.intent", resolved_intent)
        span.set_attribute("chat.route_source", decision.source)
        span.set_attribute("chat.agent", agent.name)

        agent_turn = replace(
            turn,
            intent=resolved_intent,
            history=agent_history,
        )
        reply = await agent.handle(agent_turn)

        routing_meta: dict = {
            "routed_intent": decision.intent,
            "route_source": decision.source,
            "history_window": self.history_window,
            "router_history_window": self.router_history_window,
            "history_used_for_agent": len(agent_history),
            "history_used_for_router": len(router_history),
        }
        if decision.model:
            routing_meta["router_model"] = decision.model
        if decision.usage is not None:
            routing_meta["router_tokens"] = decision.usage.to_dict()

        full_meta = {**reply.metadata, **routing_meta}
        generated = bool(full_meta.get("generated", True))
        span.set_attribute("chat.generated", generated)
        set_span_io(span, output=reply.text)
        record_chat(
            intent=resolved_intent,
            agent=reply.agent,
            generated=generated,
        )

        await self.history.append(
            sid,
            role="assistant",
            content=reply.text,
            intent=resolved_intent,
            agent=reply.agent,
            metadata=full_meta,
        )

        recent = await self.history.list_recent(sid, limit=self.history_window + 2)
        return ChatResult(
            reply=replace(reply, intent=resolved_intent, metadata=full_meta),
            session_id=sid,
            history=tuple(recent),
        )

    async def _resolve_session(self, session_id: str | None) -> str:
        if not session_id:
            return await self.history.create_session()
        try:
            sid = str(uuid.UUID(str(session_id)))
        except (ValueError, AttributeError, TypeError) as exc:
            raise ValueError(
                f"session_id inválido (debe ser UUID): {session_id!r}"
            ) from exc
        exists = await self.history.session_exists(sid)
        if not exists:
            raise ValueError(
                f"session_id no existe: {sid}. "
                'Dejá session_id="" para crear una sesión nueva.'
            )
        return sid
