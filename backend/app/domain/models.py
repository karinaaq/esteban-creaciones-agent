from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class DocumentSource:
    """Documento crudo antes de chunking."""

    source_id: str
    title: str
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class DocumentChunk:
    """Fragmento listo para embeber / indexar."""

    chunk_id: str
    source_id: str
    title: str
    content: str
    chunk_index: int
    metadata: dict[str, Any] = field(default_factory=dict)
    embedding: list[float] | None = None


@dataclass(frozen=True, slots=True)
class SearchHit:
    chunk: DocumentChunk
    score: float  # similitud coseno [0, 1] aprox.
