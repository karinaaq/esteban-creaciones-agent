from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncEngine

from app.adapters.agents.orders_agent import OrdersAgent
from app.adapters.agents.rag_agent import RagAgent
from app.adapters.agents.registry import AgentRegistry
from app.adapters.agents.static_agent import StaticReplyAgent
from app.adapters.chat_history.cached_chat_history import CachedChatHistory
from app.adapters.chat_history.postgres_chat_history import PostgresChatHistory
from app.adapters.embeddings.factory import build_embeddings
from app.adapters.guardrails.llm_judge_guardrails import LlmJudgeGuardrails
from app.adapters.guardrails.noop_guardrails import NoopGuardrails
from app.adapters.llm.bedrock_chat import BedrockChatAdapter
from app.adapters.loaders.markdown_loader import MarkdownDirectoryLoader
from app.adapters.orders.postgres_order_requests import PostgresOrderRequests
from app.adapters.prompts.yaml_prompt_repository import YamlPromptRepository
from app.adapters.router.hybrid_router import HybridRouter
from app.adapters.router.keywords import AGENT_KEYWORDS
from app.config import Settings, get_settings
from app.ports.chat_history import ChatHistoryPort
from app.ports.embeddings import EmbeddingsPort
from app.ports.guardrails import GuardrailsPort
from app.ports.llm import LlmPort
from app.ports.order_requests import OrderRequestPort
from app.ports.vector_store import VectorStorePort
from app.use_cases.handle_chat import HandleChat
from app.use_cases.ingest_documents import IngestDocuments
from app.use_cases.search_documents import SearchDocuments

DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "faqs"


@dataclass(slots=True)
class Container:
    settings: Settings
    embeddings: EmbeddingsPort
    vector_store: VectorStorePort
    history: ChatHistoryPort
    orders: OrderRequestPort
    ingest: IngestDocuments
    search: SearchDocuments
    chat: HandleChat
    agent_registry: AgentRegistry
    prompts: YamlPromptRepository


_container: Container | None = None


def set_container(container: Container) -> None:
    global _container
    _container = container


def get_container() -> Container:
    if _container is None:
        raise RuntimeError("Container not initialized")
    return _container


def _bedrock_llm(settings: Settings, model: str) -> BedrockChatAdapter:
    return BedrockChatAdapter(
        region=settings.aws_region,
        model=model,
        profile=settings.aws_profile,
    )


def create_container(
    settings: Settings,
    vector_store: VectorStorePort,
    engine: AsyncEngine,
) -> Container:
    embeddings = build_embeddings(settings)
    prompts = YamlPromptRepository()
    loader = MarkdownDirectoryLoader(DATA_DIR)
    ingest = IngestDocuments(
        loader=loader,
        embeddings=embeddings,
        vector_store=vector_store,
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
    )
    search = SearchDocuments(
        embeddings=embeddings,
        vector_store=vector_store,
        default_top_k=settings.retrieve_top_k,
        default_min_score=settings.retrieve_min_score,
    )

    postgres_history = PostgresChatHistory(engine)
    history: ChatHistoryPort = CachedChatHistory(
        postgres_history,
        max_cached_sessions=settings.chat_history_cache_sessions,
        keep_per_session=max(
            settings.chat_history_cache_keep,
            settings.chat_history_window,
            settings.router_history_window,
        ),
    )

    chat_llm: LlmPort = _bedrock_llm(settings, settings.bedrock_chat_model)
    router_llm: LlmPort | None = (
        _bedrock_llm(settings, settings.bedrock_router_model)
        if settings.router_use_llm
        else None
    )
    guardrail_llm: LlmPort = _bedrock_llm(settings, settings.bedrock_guardrail_model)

    # Input = LLM-as-judge (modelo propio, default Nova Lite); retrieve sin LLM
    guardrails: GuardrailsPort = (
        LlmJudgeGuardrails(llm=guardrail_llm, prompts=prompts)
        if settings.guardrails_enabled
        else NoopGuardrails()
    )

    orders_store: OrderRequestPort = PostgresOrderRequests(engine)

    static_agent = StaticReplyAgent()
    rag_agent = RagAgent(
        search=search,
        llm=chat_llm,
        prompts=prompts,
        guardrails=guardrails,
        generate_min_score=settings.rag_generate_min_score,
    )
    orders_agent = OrdersAgent(
        llm=chat_llm,
        prompts=prompts,
        orders=orders_store,
    )
    registry = AgentRegistry(
        {
            "greeting": static_agent,
            "farewell": static_agent,
            "thanks": static_agent,
            "general": static_agent,
            "rag": rag_agent,
            "orders": orders_agent,
            "blocked": static_agent,
        },
        default_intent="general",
    )
    router = HybridRouter(
        llm=router_llm,
        prompts=prompts,
        agent_intents=list(AGENT_KEYWORDS.keys()),
        default_intent="general",
    )
    chat = HandleChat(
        router=router,
        registry=registry,
        history=history,
        guardrails=guardrails,
        history_window=settings.chat_history_window,
        router_history_window=settings.router_history_window,
    )

    return Container(
        settings=settings,
        embeddings=embeddings,
        vector_store=vector_store,
        history=history,
        orders=orders_store,
        ingest=ingest,
        search=search,
        chat=chat,
        agent_registry=registry,
        prompts=prompts,
    )


def get_settings_dep() -> Settings:
    return get_settings()
