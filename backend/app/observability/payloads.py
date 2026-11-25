"""I/O por span estilo LangSmith (input.value / output.value) sobre OTEL gratis."""

from __future__ import annotations

_capture_enabled = True
_max_chars = 500


def configure_payloads(*, enabled: bool, max_chars: int) -> None:
    global _capture_enabled, _max_chars
    _capture_enabled = enabled
    _max_chars = max(64, int(max_chars))


def payloads_enabled() -> bool:
    return _capture_enabled


def truncate(text: str | None, max_chars: int | None = None) -> str:
    raw = text or ""
    limit = max_chars if max_chars is not None else _max_chars
    if len(raw) <= limit:
        return raw
    return raw[: limit - 1] + "…"


def set_span_io(span, *, input: str | None = None, output: str | None = None) -> None:
    """
    Tags estándar para leer cada paso como en LangSmith:
    - input.value  → qué entró al paso
    - output.value → qué salió
    """
    if not _capture_enabled or span is None:
        return
    if input is not None:
        span.set_attribute("input.value", truncate(input))
    if output is not None:
        span.set_attribute("output.value", truncate(output))
