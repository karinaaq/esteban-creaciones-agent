from __future__ import annotations

from app.adapters.guardrails.static_messages import (
    EMPTY_MESSAGES,
    TOO_LONG_MESSAGES,
    WEAK_RETRIEVE_MESSAGES,
)
from app.domain.guardrails import GuardrailResult
from app.domain.models import SearchHit
import random


class HeuristicGuardrails:
    """
    Solo para tests / fallback offline.
    El input real en runtime usa LlmJudgeGuardrails.
    """

    def __init__(self, *, max_input_chars: int = 4000) -> None:
        self._max_input_chars = max_input_chars

    async def check_input(self, message: str) -> GuardrailResult:
        text = (message or "").strip()
        if not text:
            return GuardrailResult(
                verdict="block",
                code="empty",
                message=random.choice(EMPTY_MESSAGES),
            )
        if len(text) > self._max_input_chars:
            return GuardrailResult(
                verdict="block",
                code="too_long",
                message=random.choice(TOO_LONG_MESSAGES),
                details={"length": len(text), "max": self._max_input_chars},
            )
        # Sin LLM no juzgamos malicia: allow (production usa LlmJudgeGuardrails)
        return GuardrailResult(verdict="allow", code="ok", message="ok")

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
                message=random.choice(WEAK_RETRIEVE_MESSAGES),
                details={"hit_count": 0},
            )
        best = max(hit.score for hit in hits)
        if best < generate_min_score:
            return GuardrailResult(
                verdict="abstain",
                code="weak_retrieve",
                message=random.choice(WEAK_RETRIEVE_MESSAGES),
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
