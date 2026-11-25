from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from app.domain.llm import LlmUsage

RouteSource = Literal["static", "keyword", "llm", "default"]


@dataclass(frozen=True, slots=True)
class RouteDecision:
    intent: str
    source: RouteSource
    usage: LlmUsage | None = None
    model: str | None = None
