from __future__ import annotations

from dataclasses import dataclass, replace

from app.domain.chunking import chunk_documents
from app.ports.document_loader import DocumentLoaderPort
from app.ports.embeddings import EmbeddingsPort
from app.ports.vector_store import VectorStorePort


@dataclass(frozen=True, slots=True)
class IngestResult:
    documents: int
    chunks: int
    provider: str
    model: str
    dimensions: int


@dataclass(slots=True)
class IngestDocuments:
    loader: DocumentLoaderPort
    embeddings: EmbeddingsPort
    vector_store: VectorStorePort
    chunk_size: int
    chunk_overlap: int

    async def execute(self) -> IngestResult:
        documents = await self.loader.load()
        chunks = chunk_documents(
            documents,
            chunk_size=self.chunk_size,
            overlap=self.chunk_overlap,
        )
        if not chunks:
            return IngestResult(
                documents=len(documents),
                chunks=0,
                provider=self.embeddings.provider_name,
                model=self.embeddings.model_name,
                dimensions=self.embeddings.dimensions,
            )

        await self.vector_store.ensure_schema(self.embeddings.dimensions)

        texts = [c.content for c in chunks]
        vectors = await self.embeddings.embed_documents(texts)
        if len(vectors) != len(chunks):
            raise RuntimeError("Embedding provider returned unexpected batch size")

        embedded = [
            replace(chunk, embedding=vector)
            for chunk, vector in zip(chunks, vectors, strict=True)
        ]
        stored = await self.vector_store.replace_all(
            embedded,
            provider=self.embeddings.provider_name,
            model=self.embeddings.model_name,
        )
        return IngestResult(
            documents=len(documents),
            chunks=stored,
            provider=self.embeddings.provider_name,
            model=self.embeddings.model_name,
            dimensions=self.embeddings.dimensions,
        )
