from __future__ import annotations

from functools import lru_cache

from opentelemetry import metrics


@lru_cache(maxsize=1)
def _instruments():
    meter = metrics.get_meter("esteban.creaciones", "0.1.0")
    return {
        "chat": meter.create_counter(
            "chat.requests",
            description="Chat requests completed",
            unit="1",
        ),
        "guardrail": meter.create_counter(
            "chat.guardrail_blocks",
            description="Input guardrail blocks",
            unit="1",
        ),
        "tokens": meter.create_counter(
            "llm.tokens",
            description="LLM token usage (input/output attributed separately)",
            unit="1",
        ),
    }


def record_chat(*, intent: str, agent: str, generated: bool) -> None:
    _instruments()["chat"].add(
        1,
        {
            "intent": intent or "unknown",
            "agent": agent or "unknown",
            "generated": str(bool(generated)).lower(),
        },
    )


def record_guardrail_block(*, code: str) -> None:
    _instruments()["guardrail"].add(1, {"code": code or "unknown"})


def record_llm_tokens(
    *,
    provider: str,
    model: str,
    purpose: str,
    input_tokens: int | None,
    output_tokens: int | None,
) -> None:
    attrs = {
        "provider": provider or "unknown",
        "model": model or "unknown",
        "purpose": purpose or "unknown",
    }
    tokens = _instruments()["tokens"]
    if input_tokens is not None:
        tokens.add(int(input_tokens), {**attrs, "direction": "input"})
    if output_tokens is not None:
        tokens.add(int(output_tokens), {**attrs, "direction": "output"})
