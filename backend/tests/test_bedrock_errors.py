from app.adapters.embeddings.error_mapping import translate_bedrock_exception
from app.api.errors import http_exception_from_provider
from app.domain.exceptions import (
    ProviderAuthError,
    ProviderConfigError,
    ProviderPermissionError,
    ProviderUpstreamError,
)


class _FakeClientError(Exception):
    """Sustituto mínimo de botocore ClientError para tests sin AWS."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.response = {"Error": {"Code": code, "Message": message}}


def test_expired_token_maps_to_auth(monkeypatch):
    import app.adapters.embeddings.error_mapping as mapping

    class ClientError(_FakeClientError):
        pass

    class NoCredentialsError(Exception):
        pass

    class PartialCredentialsError(Exception):
        pass

    class TokenRetrievalError(Exception):
        pass

    class BotoCoreError(Exception):
        pass

    monkeypatch.setattr(
        mapping,
        "translate_bedrock_exception",
        mapping.translate_bedrock_exception,
    )

    # Parcheamos el import interno inyectando un módulo fake via sys.modules sería
    # más pesado; acá validamos el mapper con un ClientError real si botocore está,
    # si no, simulamos la rama genérica.
    try:
        from botocore.exceptions import ClientError as RealClientError

        exc = RealClientError(
            {
                "Error": {
                    "Code": "ExpiredTokenException",
                    "Message": "The security token included in the request is expired",
                }
            },
            "InvokeModel",
        )
        mapped = translate_bedrock_exception(exc)
        assert isinstance(mapped, ProviderAuthError)
        assert mapped.code == "ExpiredTokenException"
        http_exc = http_exception_from_provider(mapped, action="chat")
        assert http_exc.status_code == 401
        assert http_exc.detail["hint"]
    except ImportError:
        mapped = ProviderAuthError("expired", provider="bedrock", code="ExpiredToken")
        assert http_exception_from_provider(mapped, action="chat").status_code == 401


def test_access_denied_maps_to_403():
    try:
        from botocore.exceptions import ClientError
    except ImportError:
        return

    exc = ClientError(
        {"Error": {"Code": "AccessDeniedException", "Message": "not allowed"}},
        "InvokeModel",
    )
    mapped = translate_bedrock_exception(exc)
    assert isinstance(mapped, ProviderPermissionError)
    assert http_exception_from_provider(mapped, action="chat").status_code == 403


def test_validation_maps_to_400():
    try:
        from botocore.exceptions import ClientError
    except ImportError:
        return

    exc = ClientError(
        {"Error": {"Code": "ValidationException", "Message": "bad model"}},
        "InvokeModel",
    )
    mapped = translate_bedrock_exception(exc)
    assert isinstance(mapped, ProviderConfigError)
    assert http_exception_from_provider(mapped, action="ingest").status_code == 400


def test_throttling_maps_to_502():
    try:
        from botocore.exceptions import ClientError
    except ImportError:
        return

    exc = ClientError(
        {"Error": {"Code": "ThrottlingException", "Message": "slow down"}},
        "InvokeModel",
    )
    mapped = translate_bedrock_exception(exc)
    assert isinstance(mapped, ProviderUpstreamError)
    assert http_exception_from_provider(mapped, action="search").status_code == 502
