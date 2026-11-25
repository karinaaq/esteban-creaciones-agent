from __future__ import annotations

from openai import AsyncOpenAI

from app.adapters.embeddings.error_mapping import translate_openai_exception
from app.domain.exceptions import ProviderConfigError, ProviderError


class OpenAIEmbeddingsAdapter:
    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        dimensions: int,
    ) -> None:
        if not api_key:
            raise ProviderConfigError(
                "OPENAI_API_KEY is required for embedding_provider=openai",
                provider="openai",
                code="MissingApiKey",
                hint="Definí OPENAI_API_KEY en el .env",
            )
        self._client = AsyncOpenAI(api_key=api_key)
        self._model = model
        self._dimensions = dimensions

    @property
    def provider_name(self) -> str:
        return "openai"

    @property
    def model_name(self) -> str:
        return self._model

    @property
    def dimensions(self) -> int:
        return self._dimensions

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        try:
            response = await self._client.embeddings.create(
                model=self._model,
                input=texts,
                dimensions=self._dimensions,
            )
        except ProviderError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise translate_openai_exception(exc) from exc

        ordered = sorted(response.data, key=lambda row: row.index)
        return [list(row.embedding) for row in ordered]

    async def embed_query(self, text: str) -> list[float]:
        vectors = await self.embed_documents([text])
        return vectors[0]
