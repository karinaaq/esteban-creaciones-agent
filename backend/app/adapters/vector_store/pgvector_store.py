from __future__ import annotations

import json
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.domain.models import DocumentChunk, SearchHit


def _vector_literal(values: list[float]) -> str:
    return "[" + ",".join(f"{v:.8f}" for v in values) + "]"


class PgVectorStore:
    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine
        self._session_factory = async_sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )
        self._dimensions: int | None = None

    async def ensure_schema(self, dimensions: int) -> None:
        async with self._engine.begin() as conn:
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            await conn.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS rag_meta (
                        id BOOLEAN PRIMARY KEY DEFAULT TRUE CHECK (id),
                        provider TEXT NOT NULL,
                        model TEXT NOT NULL,
                        dimensions INTEGER NOT NULL,
                        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                    )
                    """
                )
            )
            # Si cambia la dimensión del provider, recreamos la tabla de chunks
            existing = await conn.execute(
                text("SELECT dimensions FROM rag_meta WHERE id = TRUE")
            )
            row = existing.first()
            needs_recreate = True
            if row is None:
                needs_recreate = True
            elif int(row.dimensions) == dimensions:
                # Tabla puede existir con la misma dimensión
                exists = await conn.execute(
                    text(
                        """
                        SELECT 1
                        FROM information_schema.columns
                        WHERE table_name = 'document_chunks'
                          AND column_name = 'embedding'
                        """
                    )
                )
                needs_recreate = exists.first() is None

            # Sin índice ANN en el MVP: el corpus FAQ es chico; el scan es suficiente
            # y evita IVFFlat vacío (necesita datos para entrenar).
            if needs_recreate:
                await conn.execute(text("DROP TABLE IF EXISTS document_chunks"))
            await conn.execute(
                text(
                    f"""
                    CREATE TABLE IF NOT EXISTS document_chunks (
                        chunk_id TEXT PRIMARY KEY,
                        source_id TEXT NOT NULL,
                        title TEXT NOT NULL,
                        content TEXT NOT NULL,
                        chunk_index INTEGER NOT NULL,
                        metadata JSONB NOT NULL DEFAULT '{{}}'::jsonb,
                        embedding vector({dimensions}) NOT NULL
                    )
                    """
                )
            )
        self._dimensions = dimensions

    async def replace_all(
        self,
        chunks: list[DocumentChunk],
        *,
        provider: str,
        model: str,
    ) -> int:
        if not chunks:
            return 0
        if chunks[0].embedding is None:
            raise ValueError("chunks must include embeddings")
        dimensions = len(chunks[0].embedding)
        await self.ensure_schema(dimensions)

        async with self._session_factory() as session:
            async with session.begin():
                await session.execute(text("DELETE FROM document_chunks"))
                for chunk in chunks:
                    if chunk.embedding is None:
                        raise ValueError(f"missing embedding for {chunk.chunk_id}")
                    await session.execute(
                        text(
                            """
                            INSERT INTO document_chunks (
                                chunk_id, source_id, title, content,
                                chunk_index, metadata, embedding
                            ) VALUES (
                                :chunk_id, :source_id, :title, :content,
                                :chunk_index, CAST(:metadata AS jsonb),
                                CAST(:embedding AS vector)
                            )
                            """
                        ),
                        {
                            "chunk_id": chunk.chunk_id,
                            "source_id": chunk.source_id,
                            "title": chunk.title,
                            "content": chunk.content,
                            "chunk_index": chunk.chunk_index,
                            "metadata": json.dumps(chunk.metadata),
                            "embedding": _vector_literal(chunk.embedding),
                        },
                    )
                await session.execute(text("DELETE FROM rag_meta"))
                await session.execute(
                    text(
                        """
                        INSERT INTO rag_meta (id, provider, model, dimensions)
                        VALUES (TRUE, :provider, :model, :dimensions)
                        """
                    ),
                    {
                        "provider": provider,
                        "model": model,
                        "dimensions": dimensions,
                    },
                )
        return len(chunks)

    async def similarity_search(
        self,
        query_embedding: list[float],
        *,
        top_k: int,
        min_score: float,
    ) -> list[SearchHit]:
        # cosine distance <=> ; similarity = 1 - distance
        sql = text(
            """
            SELECT
                chunk_id,
                source_id,
                title,
                content,
                chunk_index,
                metadata,
                1 - (embedding <=> CAST(:embedding AS vector)) AS score
            FROM document_chunks
            WHERE 1 - (embedding <=> CAST(:embedding AS vector)) >= :min_score
            ORDER BY embedding <=> CAST(:embedding AS vector)
            LIMIT :top_k
            """
        )
        async with self._session_factory() as session:
            result = await session.execute(
                sql,
                {
                    "embedding": _vector_literal(query_embedding),
                    "min_score": min_score,
                    "top_k": top_k,
                },
            )
            rows = result.mappings().all()

        hits: list[SearchHit] = []
        for row in rows:
            metadata = row["metadata"]
            if isinstance(metadata, str):
                metadata = json.loads(metadata)
            chunk = DocumentChunk(
                chunk_id=row["chunk_id"],
                source_id=row["source_id"],
                title=row["title"],
                content=row["content"],
                chunk_index=row["chunk_index"],
                metadata=dict(metadata or {}),
            )
            hits.append(SearchHit(chunk=chunk, score=float(row["score"])))
        return hits

    async def count(self) -> int:
        async with self._session_factory() as session:
            try:
                result = await session.execute(
                    text("SELECT COUNT(*) AS c FROM document_chunks")
                )
            except Exception:  # noqa: BLE001
                return 0
            return int(result.scalar_one())
