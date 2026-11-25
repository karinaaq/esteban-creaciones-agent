from __future__ import annotations


class ProviderError(Exception):
    """Error de un adapter externo (embeddings, LLM, etc.)."""

    def __init__(
        self,
        message: str,
        *,
        provider: str,
        code: str | None = None,
        hint: str | None = None,
    ) -> None:
        super().__init__(message)
        self.provider = provider
        self.code = code
        self.hint = hint

    def to_detail(self) -> dict:
        detail: dict = {
            "message": str(self),
            "provider": self.provider,
            "type": type(self).__name__,
        }
        if self.code:
            detail["code"] = self.code
        if self.hint:
            detail["hint"] = self.hint
        return detail


class ProviderAuthError(ProviderError):
    """Credenciales inválidas o expiradas (401)."""


class ProviderPermissionError(ProviderError):
    """Identidad válida pero sin permiso (403)."""


class ProviderConfigError(ProviderError):
    """Modelo/región/parámetros mal configurados (400/422)."""


class ProviderUpstreamError(ProviderError):
    """Falla temporal o del lado del proveedor (502/503)."""
