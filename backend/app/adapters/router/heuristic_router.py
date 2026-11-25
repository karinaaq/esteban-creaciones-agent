"""Deprecated: usar HybridRouter."""

from app.adapters.prompts.yaml_prompt_repository import YamlPromptRepository
from app.adapters.router.hybrid_router import HybridRouter


class HeuristicRouter(HybridRouter):
    def __init__(self) -> None:
        super().__init__(
            llm=None,
            prompts=YamlPromptRepository(),
            agent_intents=["rag"],
            default_intent="general",
        )
