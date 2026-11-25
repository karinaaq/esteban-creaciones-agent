import pytest

from app.adapters.embeddings.factory import build_embeddings
from app.config import Settings
from app.domain.exceptions import ProviderConfigError


def test_openai_factory_requires_key():
    settings = Settings(embedding_provider="openai", openai_api_key="")
    with pytest.raises(ProviderConfigError, match="OPENAI_API_KEY"):
        build_embeddings(settings)


def test_local_factory_dimensions():
    settings = Settings(embedding_provider="local")
    assert settings.embedding_dimensions() == 384
