from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import Container, get_container
from app.api.errors import http_exception_from_provider
from app.api.schemas import (
    ChatAgentsResponse,
    ChatHistoryMessage,
    ChatRequest,
    ChatResponse,
    ChatSource,
    HealthResponse,
    IngestResponse,
    RagConfigResponse,
    SearchHitResponse,
    SearchRequest,
    SearchResponse,
)
from app.domain.exceptions import ProviderError

router = APIRouter()


@router.get("/health", response_model=HealthResponse, tags=["health"])
async def health(container: Container = Depends(get_container)) -> HealthResponse:
    count = await container.vector_store.count()
    return HealthResponse(
        status="ok",
        app=container.settings.app_name,
        embedding_provider=container.embeddings.provider_name,
        chunk_count=count,
    )


@router.get("/rag/config", response_model=RagConfigResponse, tags=["rag"])
async def rag_config(container: Container = Depends(get_container)) -> RagConfigResponse:
    s = container.settings
    return RagConfigResponse(
        embedding_provider=s.embedding_provider,
        embedding_dimensions=s.embedding_dimensions(),
        chunk_size=s.chunk_size,
        chunk_overlap=s.chunk_overlap,
        retrieve_top_k=s.retrieve_top_k,
        retrieve_min_score=s.retrieve_min_score,
    )


@router.post("/rag/ingest", response_model=IngestResponse, tags=["rag"])
async def ingest(container: Container = Depends(get_container)) -> IngestResponse:
    """
    Pipeline documental:
    load markdown → chunk (size+overlap) → embed (provider) → replace index en pgvector.
    """
    try:
        result = await container.ingest.execute()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ProviderError as exc:
        raise http_exception_from_provider(exc, action="ingest") from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Ingest failed: {exc}") from exc

    return IngestResponse(
        documents=result.documents,
        chunks=result.chunks,
        provider=result.provider,
        model=result.model,
        dimensions=result.dimensions,
    )


@router.post("/rag/search", response_model=SearchResponse, tags=["rag"])
async def search(
    body: SearchRequest,
    container: Container = Depends(get_container),
) -> SearchResponse:
    """
    Embeddea la query y recupera chunks con similitud coseno >= min_score.
    Todavía NO genera respuesta con LLM (eso viene después).
    """
    try:
        result = await container.search.execute(
            body.query,
            top_k=body.top_k,
            min_score=body.min_score,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ProviderError as exc:
        raise http_exception_from_provider(exc, action="search") from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Search failed: {exc}") from exc

    return SearchResponse(
        query=result.query,
        provider=result.provider,
        model=result.model,
        top_k=result.top_k,
        min_score=result.min_score,
        hits=[
            SearchHitResponse(
                chunk_id=hit.chunk.chunk_id,
                source_id=hit.chunk.source_id,
                title=hit.chunk.title,
                content=hit.chunk.content,
                chunk_index=hit.chunk.chunk_index,
                score=round(hit.score, 4),
                metadata=hit.chunk.metadata,
            )
            for hit in result.hits
        ],
    )


@router.get("/chat/agents", response_model=ChatAgentsResponse, tags=["chatbot"])
async def list_agents(
    container: Container = Depends(get_container),
) -> ChatAgentsResponse:
    return ChatAgentsResponse(
        intents=container.agent_registry.intents,
        note=(
            "Para agregar un agente: implementá AgentPort, registralo en "
            "create_container() y enseñale al Router el nuevo intent."
        ),
    )


@router.get("/chat/sessions/{session_id}", tags=["chatbot"])
async def get_session_messages(
    session_id: uuid.UUID,
    limit: int = 20,
    container: Container = Depends(get_container),
) -> dict:
    """Lee mensajes recientes (siempre con LIMIT; no descarga historial infinito)."""
    if limit < 1 or limit > 100:
        raise HTTPException(status_code=400, detail="limit must be 1..100")
    sid = str(session_id)
    exists = await container.history.session_exists(sid)
    if not exists:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")
    messages = await container.history.list_recent(sid, limit=limit)
    return {
        "session_id": sid,
        "messages": [
            {
                "role": m.role,
                "content": m.content,
                "intent": m.intent,
                "agent": m.agent,
                "created_at": m.created_at.isoformat() if m.created_at else None,
            }
            for m in messages
        ],
    }


@router.post("/chat", response_model=ChatResponse, tags=["chatbot"])
async def chat(
    body: ChatRequest,
    container: Container = Depends(get_container),
) -> ChatResponse:
    """
    Historial (cache + Postgres) → Router → Agente.

    Guardá el `session_id` de la respuesta para continuar la conversación.
    """
    try:
        result = await container.chat.execute(
            body.message,
            session_id=body.session_id or None,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ProviderError as exc:
        raise http_exception_from_provider(exc, action="chat") from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Chat failed: {exc}") from exc

    reply = result.reply
    raw_sources = reply.metadata.get("sources") or []
    sources = [
        ChatSource(
            chunk_id=s["chunk_id"],
            source_id=s["source_id"],
            title=s["title"],
            score=s["score"],
        )
        for s in raw_sources
        if isinstance(s, dict)
    ]
    history = [
        ChatHistoryMessage(
            role=m.role,
            content=m.content,
            intent=m.intent,
            agent=m.agent,
            created_at=m.created_at.isoformat() if m.created_at else None,
        )
        for m in result.history
    ]
    return ChatResponse(
        reply=reply.text,
        intent=reply.intent,
        agent=reply.agent,
        session_id=uuid.UUID(result.session_id),
        history=history,
        sources=sources,
        metadata={
            k: v
            for k, v in reply.metadata.items()
            if k not in {"sources"}
        },
    )
