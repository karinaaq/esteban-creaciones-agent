from __future__ import annotations

import json
import re
from datetime import datetime, timezone

from app.adapters.prompts.yaml_prompt_repository import YamlPromptRepository
from app.domain.chat import AgentReply, ChatTurn, format_history_for_prompt
from app.domain.orders import OrderRequest
from app.observability import get_tracer, set_span_io
from app.ports.llm import LlmPort
from app.ports.order_requests import OrderRequestPort

_FIELD_LABELS = {
    "item_description": "qué querés encargar",
    "desired_when": "para cuándo lo necesitás",
    "contact_phone": "un número de contacto",
}

_CONFIRM = (
    "¡Gracias! Ya anotamos tu solicitud. Nos vamos a comunicar con vos "
    "para pulir mejor la idea y empezar con el trabajo."
)


def _parse_orders_json(raw: str) -> dict:
    text = raw.strip()
    try:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        payload = json.loads(match.group() if match else text)
        if isinstance(payload, dict):
            return payload
    except (json.JSONDecodeError, AttributeError, TypeError, ValueError):
        pass
    return {}


def _clean_str(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.lower() in {"null", "none", "n/a", "-"}:
        return None
    return text


def _merge_draft(draft: OrderRequest, payload: dict) -> OrderRequest:
    return draft.with_updates(
        item_description=_clean_str(payload.get("item_description")),
        desired_when=_clean_str(payload.get("desired_when")),
        contact_phone=_clean_str(payload.get("contact_phone")),
    )


def _fallback_ask(missing: tuple[str, ...]) -> str:
    if not missing:
        return _CONFIRM
    label = _FIELD_LABELS.get(missing[0], missing[0])
    return f"Para registrar tu pedido, ¿me decís {label}?"


class OrdersAgent:
    """
    Recolecta: qué, para cuándo, teléfono → guarda en Postgres → confirma contacto.
    """

    def __init__(
        self,
        *,
        llm: LlmPort,
        prompts: YamlPromptRepository,
        orders: OrderRequestPort,
        prompt_name: str = "orders_collect",
    ) -> None:
        self._llm = llm
        self._prompts = prompts
        self._orders = orders
        self._prompt_name = prompt_name

    @property
    def name(self) -> str:
        return "orders"

    async def handle(self, turn: ChatTurn) -> AgentReply:
        with get_tracer().start_as_current_span("agent.orders") as span:
            session_id = turn.session_id
            if not session_id:
                text = (
                    "Para tomar tu pedido necesito una sesión activa. "
                    "Probá de nuevo en un momento."
                )
                set_span_io(span, input=turn.message, output=text)
                return AgentReply(
                    text=text,
                    intent="orders",
                    agent=self.name,
                    metadata={"error": "missing_session"},
                )

            draft = await self._orders.get_or_create_draft(session_id)
            span.set_attribute("orders.draft_id", draft.id)
            span.set_attribute("orders.missing_before", ",".join(draft.missing_fields()))
            set_span_io(
                span,
                input=(
                    f"msg={turn.message} | draft item={draft.item_description!r} "
                    f"when={draft.desired_when!r} phone={draft.contact_phone!r}"
                ),
            )

            prompt = self._prompts.get(self._prompt_name)
            missing = draft.missing_fields()
            history_text = format_history_for_prompt(turn.history)
            system = prompt.render_system(
                item_description=draft.item_description or "(vacío)",
                desired_when=draft.desired_when or "(vacío)",
                contact_phone=draft.contact_phone or "(vacío)",
                missing=", ".join(missing) if missing else "(ninguno)",
                chat_history=history_text,
            )
            user = prompt.render_user(message=turn.message)
            completion = await self._llm.complete(
                system=system,
                user=user,
                config=prompt.config,
            )
            payload = _parse_orders_json(completion.text)
            updated = _merge_draft(draft, payload)

            assistant_message = _clean_str(payload.get("assistant_message"))
            wants_complete = bool(payload.get("complete"))

            if updated.is_complete and (wants_complete or not updated.missing_fields()):
                submitted = updated.with_updates(
                    status="submitted",
                    submitted_at=datetime.now(timezone.utc),
                )
                await self._orders.save(submitted)
                text = assistant_message or _CONFIRM
                if "comunic" not in text.lower():
                    text = f"{text.rstrip()}\n\n{_CONFIRM}"
                span.set_attribute("orders.status", "submitted")
                set_span_io(span, output=text)
                return AgentReply(
                    text=text,
                    intent="orders",
                    agent=self.name,
                    metadata={
                        "order_id": submitted.id,
                        "status": "submitted",
                        "item_description": submitted.item_description,
                        "desired_when": submitted.desired_when,
                        "contact_phone": submitted.contact_phone,
                        "requested_at": (
                            submitted.requested_at.isoformat()
                            if submitted.requested_at
                            else None
                        ),
                        "llm_tokens": completion.usage.to_dict(),
                        "collected": {
                            "item_description": "COMPLETADO",
                            "desired_when": "COMPLETADO",
                            "contact_phone": "COMPLETADO",
                        },
                    },
                )

            await self._orders.save(updated)
            still_missing = updated.missing_fields()
            text = assistant_message or _fallback_ask(still_missing)
            span.set_attribute("orders.status", "draft")
            span.set_attribute("orders.missing_after", ",".join(still_missing))
            set_span_io(span, output=text)
            return AgentReply(
                text=text,
                intent="orders",
                agent=self.name,
                metadata={
                    "order_id": updated.id,
                    "status": "draft",
                    "item_description": updated.item_description,
                    "desired_when": updated.desired_when,
                    "contact_phone": updated.contact_phone,
                    "missing": list(still_missing),
                    "llm_tokens": completion.usage.to_dict(),
                    "collected": {
                        "item_description": (
                            "COMPLETADO"
                            if updated.item_description
                            else "NO_COMPLETADO"
                        ),
                        "desired_when": (
                            "COMPLETADO" if updated.desired_when else "NO_COMPLETADO"
                        ),
                        "contact_phone": (
                            "COMPLETADO" if updated.contact_phone else "NO_COMPLETADO"
                        ),
                    },
                },
            )
