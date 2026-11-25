from __future__ import annotations

from typing import Protocol

from app.domain.models import DocumentChunk, SearchHit


class VectorStorePort(Protocol):
    async def ensure_schema(self, dimensions: int) -> None:
        """Crea/valida tablas para la dimensión del provider activo."""
        ...

    async def replace_all(self, chunks: list[DocumentChunk], *, provider: str, model: str) -> int:
        """Reemplaza el índice completo (MVP simple y determinista)."""
        ...

    async def similarity_search(
        self,
        query_embedding: list[float],
        *,
        top_k: int,
        min_score: float,
    ) -> list[SearchHit]:
        """Búsqueda por similitud coseno filtrada por score mínimo."""
        ...

    async def count(self) -> int: ...
