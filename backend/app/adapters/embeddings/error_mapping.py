from __future__ import annotations

from app.domain.exceptions import (
    ProviderAuthError,
    ProviderConfigError,
    ProviderError,
    ProviderPermissionError,
    ProviderUpstreamError,
)

_AUTH_CODES = {
    "ExpiredToken",
    "ExpiredTokenException",
    "RequestExpired",
    "InvalidClientTokenId",
    "UnrecognizedClientException",
    "AuthFailure",
    "InvalidIdentityToken",
    "TokenRefreshRequired",
}

_PERMISSION_CODES = {
    "AccessDeniedException",
    "AccessDenied",
    "UnauthorizedOperation",
    "NotAuthorized",
}

_CONFIG_CODES = {
    "ValidationException",
    "ResourceNotFoundException",
    "ModelNotReadyException",
    "ModelTimeoutException",
}

_UPSTREAM_CODES = {
    "ThrottlingException",
    "TooManyRequestsException",
    "ServiceUnavailableException",
    "InternalServerException",
    "ModelErrorException",
    "ModelStreamErrorException",
    "ModelNotReadyException",
}


def translate_bedrock_exception(exc: BaseException, *, provider: str = "bedrock") -> ProviderError:
    """Convierte errores de botocore/boto3 a excepciones de dominio."""
    # Import lazy: bedrock es extra opcional
    try:
        from botocore.exceptions import (
            BotoCoreError,
            ClientError,
            NoCredentialsError,
            PartialCredentialsError,
            TokenRetrievalError,
        )
    except ImportError:
        return ProviderUpstreamError(
            f"Unexpected Bedrock error: {exc}",
            provider=provider,
            hint="Instalá el extra: pip install -e \".[bedrock]\"",
        )

    if isinstance(exc, (NoCredentialsError, PartialCredentialsError)):
        return ProviderAuthError(
            "No hay credenciales AWS configuradas para Bedrock.",
            provider=provider,
            code=type(exc).__name__,
            hint=(
                "Definí AWS_PROFILE en .env (el del SSO) y corré "
                "`aws sso login --profile <ese-perfil>`."
            ),
        )

    if isinstance(exc, TokenRetrievalError):
        return ProviderAuthError(
            "No se pudo obtener el token SSO/credenciales AWS.",
            provider=provider,
            code="TokenRetrievalError",
            hint="Ejecutá `aws sso login` o renovás el perfil SSO.",
        )

    if isinstance(exc, ClientError):
        error = (exc.response or {}).get("Error", {})
        code = str(error.get("Code") or "ClientError")
        message = str(error.get("Message") or exc)
        if code in _AUTH_CODES or "expired" in message.lower() or "invalid" in message.lower():
            return ProviderAuthError(
                f"Credenciales AWS inválidas o expiradas: {message}",
                provider=provider,
                code=code,
                hint=(
                    "Si usás SSO: `aws sso login --profile <perfil>` y asegurate de "
                    "tener AWS_PROFILE=<perfil> en .env (sin eso boto3 usa [default] viejo)."
                ),
            )
        if code in _PERMISSION_CODES:
            return ProviderPermissionError(
                f"Sin permiso para invocar Bedrock: {message}",
                provider=provider,
                code=code,
                hint="Revisá IAM: bedrock:InvokeModel y model access en la consola de Bedrock.",
            )
        if code in _CONFIG_CODES:
            return ProviderConfigError(
                f"Configuración Bedrock inválida: {message}",
                provider=provider,
                code=code,
                hint="Revisá AWS_REGION, BEDROCK_EMBEDDING_MODEL y que el modelo esté habilitado.",
            )
        if code in _UPSTREAM_CODES:
            return ProviderUpstreamError(
                f"Bedrock no disponible: {message}",
                provider=provider,
                code=code,
                hint="Reintentá más tarde; si persiste, mirá el health del servicio en AWS.",
            )
        return ProviderUpstreamError(
            f"Error Bedrock ({code}): {message}",
            provider=provider,
            code=code,
        )

    if isinstance(exc, BotoCoreError):
        return ProviderUpstreamError(
            f"Error de cliente AWS: {exc}",
            provider=provider,
            code=type(exc).__name__,
        )

    return ProviderUpstreamError(
        f"Error inesperado en Bedrock: {exc}",
        provider=provider,
        code=type(exc).__name__,
    )


def translate_openai_exception(exc: BaseException, *, provider: str = "openai") -> ProviderError:
    try:
        from openai import (
            APIConnectionError,
            APIStatusError,
            APITimeoutError,
            AuthenticationError,
            BadRequestError,
            PermissionDeniedError,
            RateLimitError,
        )
    except ImportError:
        return ProviderUpstreamError(str(exc), provider=provider)

    if isinstance(exc, AuthenticationError):
        return ProviderAuthError(
            f"OpenAI auth failed: {exc}",
            provider=provider,
            code="AuthenticationError",
            hint="Revisá OPENAI_API_KEY (válida y no expirada).",
        )
    if isinstance(exc, PermissionDeniedError):
        return ProviderPermissionError(
            f"OpenAI permission denied: {exc}",
            provider=provider,
            code="PermissionDeniedError",
        )
    if isinstance(exc, BadRequestError):
        return ProviderConfigError(
            f"OpenAI bad request: {exc}",
            provider=provider,
            code="BadRequestError",
            hint="Revisá OPENAI_EMBEDDING_MODEL y OPENAI_EMBEDDING_DIMENSIONS.",
        )
    if isinstance(exc, RateLimitError):
        return ProviderUpstreamError(
            f"OpenAI rate limit: {exc}",
            provider=provider,
            code="RateLimitError",
            hint="Esperá y reintentá; bajá concurrencia o subí cuota.",
        )
    if isinstance(exc, (APITimeoutError, APIConnectionError)):
        return ProviderUpstreamError(
            f"OpenAI connectivity: {exc}",
            provider=provider,
            code=type(exc).__name__,
        )
    if isinstance(exc, APIStatusError):
        status = getattr(exc, "status_code", None)
        if status in (401, 403):
            cls = ProviderAuthError if status == 401 else ProviderPermissionError
            return cls(
                f"OpenAI HTTP {status}: {exc}",
                provider=provider,
                code=str(status),
            )
        return ProviderUpstreamError(
            f"OpenAI HTTP {status}: {exc}",
            provider=provider,
            code=str(status) if status else "APIStatusError",
        )
    return ProviderUpstreamError(str(exc), provider=provider, code=type(exc).__name__)
