from __future__ import annotations

from typing import Protocol


class EmbeddingsPort(Protocol):
    """Puerto de embeddings — intercambiable (local / openai / bedrock)."""

    @property
    def provider_name(self) -> str: ...

    @property
    def model_name(self) -> str: ...

    @property
    def dimensions(self) -> int: ...

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Embeddea varios textos (batch)."""
        ...

    async def embed_query(self, text: str) -> list[float]:
        """Embeddea una query de búsqueda."""
        ...
