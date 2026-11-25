from __future__ import annotations

from app.adapters.embeddings.bedrock_embeddings import BedrockEmbeddingsAdapter
from app.adapters.embeddings.local_embeddings import LocalEmbeddingsAdapter
from app.adapters.embeddings.openai_embeddings import OpenAIEmbeddingsAdapter
from app.config import Settings
from app.ports.embeddings import EmbeddingsPort


def build_embeddings(settings: Settings) -> EmbeddingsPort:
    provider = settings.embedding_provider
    if provider == "openai":
        return OpenAIEmbeddingsAdapter(
            api_key=settings.openai_api_key,
            model=settings.openai_embedding_model,
            dimensions=settings.openai_embedding_dimensions,
        )
    if provider == "bedrock":
        return BedrockEmbeddingsAdapter(
            region=settings.aws_region,
            model=settings.bedrock_embedding_model,
            dimensions=settings.bedrock_embedding_dimensions,
            profile=settings.aws_profile,
        )
    if provider == "local":
        return LocalEmbeddingsAdapter(
            model_name=settings.local_embedding_model,
            dimensions=settings.embedding_dimensions(),
        )
    raise ValueError(f"Unknown embedding provider: {provider}")
