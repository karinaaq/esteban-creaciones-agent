from __future__ import annotations

from pathlib import Path

from app.domain.models import DocumentSource


class MarkdownDirectoryLoader:
    """Carga cada archivo .md como un DocumentSource."""

    def __init__(self, directory: Path) -> None:
        self._directory = directory

    async def load(self) -> list[DocumentSource]:
        if not self._directory.exists():
            raise FileNotFoundError(f"Documents directory not found: {self._directory}")

        documents: list[DocumentSource] = []
        for path in sorted(self._directory.glob("*.md")):
            text = path.read_text(encoding="utf-8").strip()
            if not text:
                continue
            title = path.stem.replace("-", " ").replace("_", " ").title()
            # Si el archivo empieza con # título, usarlo
            first_line = text.splitlines()[0]
            if first_line.startswith("# "):
                title = first_line.lstrip("# ").strip()
            documents.append(
                DocumentSource(
                    source_id=path.stem,
                    title=title,
                    text=text,
                    metadata={"path": str(path.name), "loader": "markdown"},
                )
            )
        return documents
