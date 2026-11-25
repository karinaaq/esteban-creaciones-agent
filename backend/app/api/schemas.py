from __future__ import annotations

import uuid

from pydantic import BaseModel, Field, field_validator


class HealthResponse(BaseModel):
    status: str
    app: str
    embedding_provider: str
    chunk_count: int


class RagConfigResponse(BaseModel):
    embedding_provider: str
    embedding_dimensions: int
    chunk_size: int
    chunk_overlap: int
    retrieve_top_k: int
    retrieve_min_score: float


class IngestResponse(BaseModel):
    documents: int
    chunks: int
    provider: str
    model: str
    dimensions: int


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    top_k: int | None = Field(default=None, ge=1, le=50)
    min_score: float | None = Field(default=None, ge=0.0, le=1.0)


class SearchHitResponse(BaseModel):
    chunk_id: str
    source_id: str
    title: str
    content: str
    chunk_index: int
    score: float
    metadata: dict


class SearchResponse(BaseModel):
    query: str
    provider: str
    model: str
    top_k: int
    min_score: float
    hits: list[SearchHitResponse]


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    # "" / null = nueva sesión. Pegá el UUID de una respuesta previa para continuar.
    session_id: str = Field(
        default="",
        description='Vacío ("") crea sesión nueva. UUID de /chat para continuar.',
        examples=[""],
    )

    @field_validator("session_id", mode="before")
    @classmethod
    def normalize_session_id(cls, value: object) -> str:
        if value is None:
            return ""
        if isinstance(value, uuid.UUID):
            return str(value)
        return str(value).strip()


class ChatSource(BaseModel):
    chunk_id: str
    source_id: str
    title: str
    score: float


class ChatHistoryMessage(BaseModel):
    role: str
    content: str
    intent: str | None = None
    agent: str | None = None
    created_at: str | None = None


class ChatResponse(BaseModel):
    reply: str
    intent: str
    agent: str
    session_id: uuid.UUID
    history: list[ChatHistoryMessage] = Field(default_factory=list)
    sources: list[ChatSource] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)


class ChatAgentsResponse(BaseModel):
    intents: list[str]
    note: str
