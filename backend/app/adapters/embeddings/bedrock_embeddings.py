from __future__ import annotations

import json
from functools import lru_cache

from app.adapters.embeddings.error_mapping import translate_bedrock_exception
from app.domain.exceptions import ProviderError


@lru_cache(maxsize=4)
def _bedrock_client(region: str, profile: str):
    try:
        import boto3
    except ImportError as exc:  # pragma: no cover
        raise ImportError(
            "Instalá el extra bedrock: pip install -e \".[bedrock]\""
        ) from exc

    session_kwargs = {}
    if profile:
        session_kwargs["profile_name"] = profile
    session = boto3.Session(**session_kwargs)
    return session.client("bedrock-runtime", region_name=region)


class BedrockEmbeddingsAdapter:
    """Amazon Bedrock (Titan Embeddings). Requiere AWS credentials / SSO profile."""

    def __init__(
        self,
        *,
        region: str,
        model: str,
        dimensions: int,
        profile: str = "",
    ) -> None:
        self._region = region
        self._profile = profile
        self._model = model
        self._dimensions = dimensions
        try:
            self._client = _bedrock_client(region, profile or "")
        except Exception as exc:  # noqa: BLE001
            mapped = translate_bedrock_exception(exc)
            raise mapped from exc

    @property
    def provider_name(self) -> str:
        return "bedrock"

    @property
    def model_name(self) -> str:
        return self._model

    @property
    def dimensions(self) -> int:
        return self._dimensions

    def _embed_one(self, text: str) -> list[float]:
        body = {
            "inputText": text,
            "dimensions": self._dimensions,
            "normalize": True,
        }
        try:
            response = self._client.invoke_model(
                modelId=self._model,
                contentType="application/json",
                accept="application/json",
                body=json.dumps(body),
            )
            payload = json.loads(response["body"].read())
        except ProviderError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise translate_bedrock_exception(exc) from exc

        embedding = payload.get("embedding")
        if not embedding:
            raise translate_bedrock_exception(
                RuntimeError(f"Bedrock response without embedding: {payload}")
            )
        return list(embedding)

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        import asyncio

        if not texts:
            return []

        def _run() -> list[list[float]]:
            return [self._embed_one(text) for text in texts]

        try:
            return await asyncio.to_thread(_run)
        except ProviderError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise translate_bedrock_exception(exc) from exc

    async def embed_query(self, text: str) -> list[float]:
        vectors = await self.embed_documents([text])
        return vectors[0]
