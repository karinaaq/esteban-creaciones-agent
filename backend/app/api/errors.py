from __future__ import annotations

from fastapi import HTTPException

from app.domain.exceptions import (
    ProviderAuthError,
    ProviderConfigError,
    ProviderError,
    ProviderPermissionError,
    ProviderUpstreamError,
)


def http_exception_from_provider(exc: ProviderError, *, action: str) -> HTTPException:
    """
    Traduce errores de provider a HTTP semántico.

    - Auth → 401
    - Permission → 403
    - Config → 400
    - Upstream → 502
    """
    if isinstance(exc, ProviderAuthError):
        status = 401
    elif isinstance(exc, ProviderPermissionError):
        status = 403
    elif isinstance(exc, ProviderConfigError):
        status = 400
    elif isinstance(exc, ProviderUpstreamError):
        status = 502
    else:
        status = 502

    detail = exc.to_detail()
    detail["action"] = action
    return HTTPException(status_code=status, detail=detail)
