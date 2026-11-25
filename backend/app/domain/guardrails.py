from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

GuardrailVerdict = Literal["allow", "block", "abstain"]


@dataclass(frozen=True, slots=True)
class GuardrailResult:
    verdict: GuardrailVerdict
    code: str
    message: str
    details: dict | None = None

    @property
    def allowed(self) -> bool:
        return self.verdict == "allow"
