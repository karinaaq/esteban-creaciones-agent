from __future__ import annotations

import asyncio
from typing import Any


class LocalEmbeddingsAdapter:
    """
    Embeddings gratis vía FastEmbed (ONNX, sin PyTorch pesado).

    Default: BAAI/bge-small-en-v1.5 (384 dims). Sirve para demos multilingües básicas;
    para español de producción se puede cambiar el modelo en .env.
    """

    def __init__(self, *, model_name: str, dimensions: int = 384) -> None:
        self._model_name = model_name
        self._dimensions = dimensions
        self._model: Any | None = None

    @property
    def provider_name(self) -> str:
        return "local"

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def dimensions(self) -> int:
        return self._dimensions

    def _ensure_model(self) -> Any:
        if self._model is not None:
            return self._model
        try:
            from fastembed import TextEmbedding
        except ImportError as exc:  # pragma: no cover
            raise ImportError(
                'Instalá el extra local: pip install -e ".[local]"'
            ) from exc
        # Un token HF vencido en ~/.cache/huggingface/token rompe descargas públicas.
        import os

        os.environ.setdefault("HF_HUB_DISABLE_IMPLICIT_TOKEN", "1")
        self._model = TextEmbedding(model_name=self._model_name)
        return self._model

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        def _encode() -> list[list[float]]:
            model = self._ensure_model()
            # fastembed yields numpy arrays / lists
            return [list(map(float, vector)) for vector in model.embed(texts)]

        return await asyncio.to_thread(_encode)

    async def embed_query(self, text: str) -> list[float]:
        if not text.strip():
            raise ValueError("query text must not be empty")

        def _encode() -> list[float]:
            model = self._ensure_model()
            vector = next(model.query_embed(text))
            return list(map(float, vector))

        return await asyncio.to_thread(_encode)
