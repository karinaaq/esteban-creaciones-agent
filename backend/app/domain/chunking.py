"""Chunking por caracteres con overlap — simple, predecible y barato."""

from __future__ import annotations

import hashlib
import re

from app.domain.models import DocumentChunk, DocumentSource


def _stable_chunk_id(source_id: str, index: int, content: str) -> str:
    digest = hashlib.sha256(f"{source_id}:{index}:{content}".encode()).hexdigest()[:16]
    return f"{source_id}-{index}-{digest}"


def split_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    if chunk_size <= 0:
        raise ValueError("chunk_size must be > 0")
    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap must be >= 0 and < chunk_size")

    normalized = re.sub(r"\n{3,}", "\n\n", text.strip())
    if not normalized:
        return []
    if len(normalized) <= chunk_size:
        return [normalized]

    chunks: list[str] = []
    start = 0
    length = len(normalized)
    while start < length:
        end = min(start + chunk_size, length)
        # Preferir corte en espacio/párrafo hacia atrás
        if end < length:
            window = normalized[start:end]
            cut = max(window.rfind("\n\n"), window.rfind("\n"), window.rfind(" "))
            if cut >= chunk_size // 4:
                end = start + cut
        piece = normalized[start:end].strip()
        if piece:
            chunks.append(piece)
        if end >= length:
            break
        start = max(0, end - overlap)
        if start >= end:
            start = end
    return chunks


def chunk_documents(
    documents: list[DocumentSource],
    *,
    chunk_size: int,
    overlap: int,
) -> list[DocumentChunk]:
    result: list[DocumentChunk] = []
    for doc in documents:
        parts = split_text(doc.text, chunk_size=chunk_size, overlap=overlap)
        for idx, part in enumerate(parts):
            result.append(
                DocumentChunk(
                    chunk_id=_stable_chunk_id(doc.source_id, idx, part),
                    source_id=doc.source_id,
                    title=doc.title,
                    content=part,
                    chunk_index=idx,
                    metadata={
                        **doc.metadata,
                        "char_count": len(part),
                    },
                )
            )
    return result
