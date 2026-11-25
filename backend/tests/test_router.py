import pytest

from app.adapters.prompts.yaml_prompt_repository import YamlPromptRepository
from app.adapters.router.hybrid_router import HybridRouter
from app.domain.chat import ChatTurn
from app.domain.llm import LlmCompletion, LlmInferenceConfig, LlmUsage


def _router(llm=None) -> HybridRouter:
    return HybridRouter(
        llm=llm,
        prompts=YamlPromptRepository(),
        agent_intents=["rag"],
    )


@pytest.mark.asyncio
async def test_greeting_is_static_intent():
    decision = await _router().route(ChatTurn(message="Hola!"))
    assert decision.intent == "greeting"
    assert decision.source == "static"
    assert decision.usage is None


@pytest.mark.asyncio
async def test_farewell_is_static_intent():
    decision = await _router().route(ChatTurn(message="Chau, nos vemos"))
    assert decision.intent == "farewell"
    assert decision.source == "static"


@pytest.mark.asyncio
async def test_thanks_is_static_intent():
    decision = await _router().route(ChatTurn(message="Muchas gracias"))
    assert decision.intent == "thanks"


@pytest.mark.asyncio
async def test_agent_keyword_routes_to_rag():
    decision = await _router().route(ChatTurn(message="Cuanto tarda un centro de mesa?"))
    assert decision.intent == "rag"
    assert decision.source == "keyword"


@pytest.mark.asyncio
async def test_orders_keyword_beats_rag_on_tie():
    decision = await _router().route(
        ChatTurn(message="Quiero encargar un disfraz para diciembre")
    )
    assert decision.intent == "orders"
    assert decision.source == "keyword"


@pytest.mark.asyncio
async def test_greeting_plus_faq_prefers_rag():
    decision = await _router().route(ChatTurn(message="Hola, cuanto tarda una carpeta?"))
    assert decision.intent == "rag"
    assert decision.source == "keyword"


@pytest.mark.asyncio
async def test_unknown_without_llm_goes_general():
    decision = await _router(llm=None).route(ChatTurn(message="asdf qwerty"))
    assert decision.intent == "general"
    assert decision.source == "default"


class _FakeLlm:
    provider_name = "fake"
    model_name = "fake-model"

    async def complete(self, *, system: str, user: str, config: LlmInferenceConfig):
        assert config.max_tokens == 40
        assert "Intent" in system or "intent" in system.lower()
        return LlmCompletion(
            text='{"intent":"rag"}',
            usage=LlmUsage(input_tokens=20, output_tokens=5),
            provider=self.provider_name,
            model=self.model_name,
        )


@pytest.mark.asyncio
async def test_llm_used_when_no_keywords_reports_usage():
    decision = await _router(llm=_FakeLlm()).route(
        ChatTurn(message="necesito info del taller creativo")
    )
    assert decision.intent == "rag"
    assert decision.source == "llm"
    assert decision.usage is not None
    assert decision.usage.total_tokens == 25
