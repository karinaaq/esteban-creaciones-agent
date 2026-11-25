from __future__ import annotations

import json
import re

from app.adapters.prompts.yaml_prompt_repository import YamlPromptRepository
from app.adapters.router.keywords import (
    AGENT_KEYWORDS,
    FAREWELL_KEYWORDS,
    GREETING_KEYWORDS,
    THANKS_KEYWORDS,
)
from app.domain.chat import ChatTurn, format_history_for_prompt
from app.domain.routing import RouteDecision
from app.observability import get_tracer, set_span_io
from app.ports.llm import LlmPort

_STATIC_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("greeting", GREETING_KEYWORDS),
    ("farewell", FAREWELL_KEYWORDS),
    ("thanks", THANKS_KEYWORDS),
)


def _contains_keyword(text: str, keywords: tuple[str, ...]) -> bool:
    return any(keyword in text for keyword in keywords)


def _match_static_intent(text: str) -> str | None:
    for intent, keywords in _STATIC_RULES:
        if _contains_keyword(text, keywords):
            if intent == "greeting" and _best_agent_intent(text) is not None:
                return None
            return intent
    return None


# Empate keyword: pedidos gana sobre FAQ (encargar un disfraz → orders)
_INTENT_TIE_PRIORITY: dict[str, int] = {
    "orders": 2,
    "rag": 1,
}


def _best_agent_intent(text: str) -> str | None:
    best_intent: str | None = None
    best_score = 0
    best_priority = -1
    for intent, keywords in AGENT_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in text)
        priority = _INTENT_TIE_PRIORITY.get(intent, 0)
        if score > best_score or (score == best_score and score > 0 and priority > best_priority):
            best_score = score
            best_intent = intent
            best_priority = priority
    return best_intent if best_score > 0 else None


def _parse_intent(raw: str, allowed: set[str], default: str) -> str:
    text = raw.strip()
    try:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        payload = json.loads(match.group() if match else text)
        intent = str(payload.get("intent", "")).strip().lower()
        if intent in allowed:
            return intent
    except (json.JSONDecodeError, AttributeError, TypeError):
        pass

    lowered = text.lower()
    for intent in allowed:
        if re.search(rf"\b{re.escape(intent)}\b", lowered):
            return intent
    return default


class HybridRouter:
    """
    1) Keywords estáticas → greeting / farewell / thanks (sin LLM)
    2) Keywords de AGENT_KEYWORDS → agente (sin LLM)
    3) Si no hay match → LLM con prompt YAML router_classify
    """

    def __init__(
        self,
        *,
        llm: LlmPort | None,
        prompts: YamlPromptRepository,
        agent_intents: list[str],
        default_intent: str = "general",
        router_prompt_name: str = "router_classify",
    ) -> None:
        self._llm = llm
        self._prompts = prompts
        self._router_prompt_name = router_prompt_name
        self._agent_intents = list(agent_intents)
        for key in AGENT_KEYWORDS:
            if key not in self._agent_intents:
                self._agent_intents.append(key)
        self._default_intent = default_intent

    async def route(self, turn: ChatTurn) -> RouteDecision:
        with get_tracer().start_as_current_span("router.route") as span:
            text = turn.message.strip().lower()
            if not text:
                decision = RouteDecision(intent=self._default_intent, source="default")
            else:
                static_intent = _match_static_intent(text)
                if static_intent:
                    decision = RouteDecision(intent=static_intent, source="static")
                else:
                    agent_intent = _best_agent_intent(text)
                    if agent_intent:
                        decision = RouteDecision(intent=agent_intent, source="keyword")
                    else:
                        decision = await self._route_with_llm(turn)

            span.set_attribute("router.intent", decision.intent)
            span.set_attribute("router.source", decision.source)
            set_span_io(
                span,
                input=turn.message,
                output=f"intent={decision.intent} source={decision.source}",
            )
            return decision

    async def _route_with_llm(self, turn: ChatTurn) -> RouteDecision:
        allowed = set(self._agent_intents) | {self._default_intent}
        if self._llm is None:
            return RouteDecision(intent=self._default_intent, source="default")

        prompt = self._prompts.get(self._router_prompt_name)
        history_text = format_history_for_prompt(turn.history)
        system = prompt.render_system(
            allowed=", ".join(sorted(allowed)),
            chat_history=history_text,
        )
        user = (
            prompt.render_user(message=turn.message, chat_history=history_text)
            if prompt.user_template
            else f"Historial reciente:\n{history_text}\n\nMensaje del usuario:\n{turn.message}"
        )
        completion = await self._llm.complete(
            system=system,
            user=user,
            config=prompt.config,
        )
        intent = _parse_intent(completion.text, allowed, self._default_intent)
        return RouteDecision(
            intent=intent,
            source="llm",
            usage=completion.usage,
            model=completion.model,
        )
