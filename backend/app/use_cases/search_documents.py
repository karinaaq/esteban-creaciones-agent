from __future__ import annotations

from dataclasses import dataclass

from app.domain.models import SearchHit
from app.ports.embeddings import EmbeddingsPort
from app.ports.vector_store import VectorStorePort


@dataclass(frozen=True, slots=True)
class SearchResult:
    query: str
    hits: list[SearchHit]
    provider: str
    model: str
    top_k: int
    min_score: float


@dataclass(slots=True)
class SearchDocuments:
    embeddings: EmbeddingsPort
    vector_store: VectorStorePort
    default_top_k: int
    default_min_score: float

    async def execute(
        self,
        query: str,
        *,
        top_k: int | None = None,
        min_score: float | None = None,
    ) -> SearchResult:
        cleaned = query.strip()
        if not cleaned:
            raise ValueError("query must not be empty")

        k = top_k if top_k is not None else self.default_top_k
        threshold = (
            min_score if min_score is not None else self.default_min_score
        )
        if k <= 0:
            raise ValueError("top_k must be > 0")

        vector = await self.embeddings.embed_query(cleaned)
        hits = await self.vector_store.similarity_search(
            vector,
            top_k=k,
            min_score=threshold,
        )
        return SearchResult(
            query=cleaned,
            hits=hits,
            provider=self.embeddings.provider_name,
            model=self.embeddings.model_name,
            top_k=k,
            min_score=threshold,
        )
