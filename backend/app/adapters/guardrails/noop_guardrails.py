from __future__ import annotations

from app.domain.guardrails import GuardrailResult
from app.domain.models import SearchHit


class NoopGuardrails:
    """Desactiva guardrails (solo debug)."""

    async def check_input(self, message: str) -> GuardrailResult:
        return GuardrailResult(verdict="allow", code="noop", message="ok")

    def check_retrieve(
        self,
        hits: list[SearchHit],
        *,
        generate_min_score: float,
    ) -> GuardrailResult:
        return GuardrailResult(
            verdict="allow",
            code="noop",
            message="ok",
            details={"hit_count": len(hits)},
        )
