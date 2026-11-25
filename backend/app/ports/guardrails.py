from __future__ import annotations

from typing import Protocol

from app.domain.guardrails import GuardrailResult
from app.domain.models import SearchHit


class GuardrailsPort(Protocol):
    async def check_input(self, message: str) -> GuardrailResult:
        """Valida el mensaje del usuario (puede usar LLM-as-judge)."""
        ...

    def check_retrieve(
        self,
        hits: list[SearchHit],
        *,
        generate_min_score: float,
    ) -> GuardrailResult:
        """Calidad mínima del retrieve antes de generar (sin LLM)."""
        ...
