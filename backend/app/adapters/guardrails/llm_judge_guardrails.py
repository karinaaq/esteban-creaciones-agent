from __future__ import annotations

import json
import random
import re

from app.adapters.guardrails.static_messages import (
    BLOCK_MESSAGES_BY_CATEGORY,
    EMPTY_MESSAGES,
    TOO_LONG_MESSAGES,
    WEAK_RETRIEVE_MESSAGES,
)
from app.adapters.prompts.yaml_prompt_repository import YamlPromptRepository
from app.domain.guardrails import GuardrailResult
from app.domain.models import SearchHit
from app.observability import get_tracer, set_span_io
from app.ports.llm import LlmPort


def _pick(messages: tuple[str, ...]) -> str:
    return random.choice(messages)


def _message_for_category(category: str) -> str:
    key = (category or "other").strip().lower()
    options = BLOCK_MESSAGES_BY_CATEGORY.get(key) or BLOCK_MESSAGES_BY_CATEGORY["other"]
    return _pick(options)


def _parse_judge(raw: str) -> tuple[bool, str]:
    text = raw.strip()
    try:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        payload = json.loads(match.group() if match else text)
        unsafe = bool(payload.get("unsafe", False))
        category = str(payload.get("category") or ("unsafe" if unsafe else "safe"))
        return unsafe, category.lower()
    except (json.JSONDecodeError, AttributeError, TypeError, ValueError):
        # Fail-open en parse error: no bloquear FAQ por un JSON roto
        return False, "safe"


class LlmJudgeGuardrails:
    """
    Input: LLM-as-a-judge (prompt YAML) → si unsafe=true, mensaje estático (tupla).
    Retrieve: heurística por score (sin LLM, barato).
    """

    def __init__(
        self,
        *,
        llm: LlmPort,
        prompts: YamlPromptRepository,
        max_input_chars: int = 4000,
        judge_prompt_name: str = "input_guardrail_judge",
    ) -> None:
        self._llm = llm
        self._prompts = prompts
        self._max_input_chars = max_input_chars
        self._judge_prompt_name = judge_prompt_name

    async def check_input(self, message: str) -> GuardrailResult:
        with get_tracer().start_as_current_span("guardrail.input") as span:
            text = (message or "").strip()
            set_span_io(span, input=text)
            if not text:
                result = GuardrailResult(
                    verdict="block",
                    code="empty",
                    message=_pick(EMPTY_MESSAGES),
                )
                span.set_attribute("guardrail.code", "empty")
                span.set_attribute("guardrail.verdict", "block")
                set_span_io(span, output=f"block:{result.code} | {result.message}")
                return result
            if len(text) > self._max_input_chars:
                result = GuardrailResult(
                    verdict="block",
                    code="too_long",
                    message=_pick(TOO_LONG_MESSAGES),
                    details={"length": len(text), "max": self._max_input_chars},
                )
                span.set_attribute("guardrail.code", "too_long")
                span.set_attribute("guardrail.verdict", "block")
                set_span_io(span, output=f"block:{result.code} | {result.message}")
                return result

            prompt = self._prompts.get(self._judge_prompt_name)
            system = prompt.render_system()
            user = prompt.render_user(message=text)
            completion = await self._llm.complete(
                system=system,
                user=user,
                config=prompt.config,
            )
            unsafe, category = _parse_judge(completion.text)
            span.set_attribute("guardrail.judge", True)
            span.set_attribute("guardrail.category", category)
            span.set_attribute("guardrail.unsafe", unsafe)
            if not unsafe:
                span.set_attribute("guardrail.verdict", "allow")
                span.set_attribute("guardrail.code", "ok")
                set_span_io(
                    span,
                    output=f"allow | category={category} | judge={completion.text}",
                )
                return GuardrailResult(
                    verdict="allow",
                    code="ok",
                    message="ok",
                    details={
                        "judge": True,
                        "category": category,
                        "tokens": completion.usage.to_dict(),
                        "model": completion.model,
                    },
                )

            code = category if category != "safe" else "unsafe"
            result = GuardrailResult(
                verdict="block",
                code=code,
                message=_message_for_category(code),
                details={
                    "judge": True,
                    "unsafe": True,
                    "category": category,
                    "tokens": completion.usage.to_dict(),
                    "model": completion.model,
                },
            )
            span.set_attribute("guardrail.verdict", "block")
            span.set_attribute("guardrail.code", code)
            set_span_io(
                span,
                output=f"block:{code} | judge={completion.text} | reply={result.message}",
            )
            return result

    def check_retrieve(
        self,
        hits: list[SearchHit],
        *,
        generate_min_score: float,
    ) -> GuardrailResult:
        if not hits:
            return GuardrailResult(
                verdict="abstain",
                code="no_hits",
                message=_pick(WEAK_RETRIEVE_MESSAGES),
                details={"hit_count": 0},
            )
        best = max(hit.score for hit in hits)
        if best < generate_min_score:
            return GuardrailResult(
                verdict="abstain",
                code="weak_retrieve",
                message=_pick(WEAK_RETRIEVE_MESSAGES),
                details={
                    "best_score": round(best, 4),
                    "generate_min_score": generate_min_score,
                    "hit_count": len(hits),
                },
            )
        return GuardrailResult(
            verdict="allow",
            code="ok",
            message="ok",
            details={"best_score": round(best, 4), "hit_count": len(hits)},
        )
