from dataclasses import dataclass

import pytest

from app.adapters.agents.rag_agent import RagAgent
from app.adapters.guardrails.heuristic_guardrails import HeuristicGuardrails
from app.adapters.prompts.yaml_prompt_repository import YamlPromptRepository
from app.domain.chat import ChatTurn
from app.domain.llm import LlmCompletion, LlmInferenceConfig, LlmUsage
from app.domain.models import DocumentChunk, SearchHit
from app.use_cases.search_documents import SearchResult


@dataclass
class _FakeSearch:
    hits: list[SearchHit]

    async def execute(self, query: str, *, top_k=None, min_score=None):
        return SearchResult(
            query=query,
            hits=self.hits,
            provider="fake-embed",
            model="fake-embed-model",
            top_k=top_k or 5,
            min_score=min_score or 0.3,
        )


class _FakeLlm:
    provider_name = "fake"
    model_name = "fake-chat"

    async def complete(self, *, system: str, user: str, config: LlmInferenceConfig):
        assert "10 dias" in system or "10 días" in system or "contexto" in system.lower()
        assert config.max_tokens == 220
        return LlmCompletion(
            text="Un centro de mesa suele pedir unos 10 dias de anticipacion.",
            usage=LlmUsage(input_tokens=100, output_tokens=30),
            provider=self.provider_name,
            model=self.model_name,
        )


@pytest.mark.asyncio
async def test_rag_agent_generates_from_context():
    hits = [
        SearchHit(
            chunk=DocumentChunk(
                chunk_id="c1",
                source_id="plazos",
                title="Plazos",
                content="Los centros de mesa requieren alrededor de 10 dias.",
                chunk_index=0,
            ),
            score=0.91,
        )
    ]
    agent = RagAgent(
        search=_FakeSearch(hits),  # type: ignore[arg-type]
        llm=_FakeLlm(),
        prompts=YamlPromptRepository(),
        guardrails=HeuristicGuardrails(),
        generate_min_score=0.45,
    )
    reply = await agent.handle(ChatTurn(message="cuanto tarda un centro de mesa?"))
    assert reply.metadata["generated"] is True
    assert reply.metadata["llm_tokens"]["total_tokens"] == 130
    assert "10 dias" in reply.text.lower() or "10" in reply.text


@pytest.mark.asyncio
async def test_rag_agent_empty_uses_yaml_empty_reply():
    agent = RagAgent(
        search=_FakeSearch([]),  # type: ignore[arg-type]
        llm=_FakeLlm(),
        prompts=YamlPromptRepository(),
        guardrails=HeuristicGuardrails(),
        generate_min_score=0.45,
    )
    reply = await agent.handle(ChatTurn(message="algo inexistente"))
    assert reply.metadata["generated"] is False
    assert reply.metadata["guardrail"]["code"] in {"no_hits", "weak_retrieve"}


@pytest.mark.asyncio
async def test_rag_agent_abstains_on_weak_score():
    hits = [
        SearchHit(
            chunk=DocumentChunk(
                chunk_id="c1",
                source_id="plazos",
                title="Plazos",
                content="Los centros de mesa requieren alrededor de 10 dias.",
                chunk_index=0,
            ),
            score=0.20,
        )
    ]
    agent = RagAgent(
        search=_FakeSearch(hits),  # type: ignore[arg-type]
        llm=_FakeLlm(),
        prompts=YamlPromptRepository(),
        guardrails=HeuristicGuardrails(),
        generate_min_score=0.45,
    )
    reply = await agent.handle(ChatTurn(message="cuanto tarda?"))
    assert reply.metadata["generated"] is False
    assert reply.metadata["guardrail"]["code"] == "weak_retrieve"
