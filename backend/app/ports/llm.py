from __future__ import annotations

from typing import Protocol

from app.domain.llm import LlmCompletion, LlmInferenceConfig


class LlmPort(Protocol):
    """Puerto de LLM: el caller pasa system/user + config del PromptSpec."""

    @property
    def provider_name(self) -> str: ...

    @property
    def model_name(self) -> str: ...

    async def complete(
        self,
        *,
        system: str,
        user: str,
        config: LlmInferenceConfig,
    ) -> LlmCompletion:
        ...
