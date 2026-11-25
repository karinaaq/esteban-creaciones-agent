from __future__ import annotations

from typing import Protocol

from app.domain.models import DocumentSource


class DocumentLoaderPort(Protocol):
    async def load(self) -> list[DocumentSource]:
        """Carga documentos crudos desde una fuente (markdown, etc.)."""
        ...
