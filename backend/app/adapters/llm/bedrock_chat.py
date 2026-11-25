from __future__ import annotations

from functools import lru_cache

from app.adapters.embeddings.error_mapping import translate_bedrock_exception
from app.domain.exceptions import ProviderError
from app.domain.llm import LlmCompletion, LlmInferenceConfig, LlmUsage
from app.observability import get_tracer, record_llm_tokens, set_span_error, set_span_io


@lru_cache(maxsize=4)
def _bedrock_runtime(region: str, profile: str):
    import boto3

    session_kwargs = {}
    if profile:
        session_kwargs["profile_name"] = profile
    session = boto3.Session(**session_kwargs)
    return session.client("bedrock-runtime", region_name=region)


def _usage_from_converse(response: dict) -> LlmUsage:
    usage = response.get("usage") or {}
    # Bedrock Converse: inputTokens / outputTokens
    input_tokens = usage.get("inputTokens")
    output_tokens = usage.get("outputTokens")
    return LlmUsage(
        input_tokens=int(input_tokens) if input_tokens is not None else None,
        output_tokens=int(output_tokens) if output_tokens is not None else None,
    )


class BedrockChatAdapter:
    """LLM de texto vía Bedrock Converse. No decide max_tokens: los recibe del PromptSpec."""

    def __init__(
        self,
        *,
        region: str,
        model: str,
        profile: str = "",
    ) -> None:
        self._region = region
        self._model = model
        self._profile = profile
        try:
            self._client = _bedrock_runtime(region, profile or "")
        except Exception as exc:  # noqa: BLE001
            raise translate_bedrock_exception(exc) from exc

    @property
    def provider_name(self) -> str:
        return "bedrock"

    @property
    def model_name(self) -> str:
        return self._model

    async def complete(
        self,
        *,
        system: str,
        user: str,
        config: LlmInferenceConfig,
    ) -> LlmCompletion:
        import asyncio

        tracer = get_tracer()
        with tracer.start_as_current_span("llm.complete") as span:
            span.set_attribute("llm.provider", self.provider_name)
            span.set_attribute("llm.model", self._model)
            span.set_attribute("llm.max_tokens", config.max_tokens)
            span.set_attribute("llm.temperature", float(config.temperature))
            set_span_io(
                span,
                input=f"system:\n{system}\n\nuser:\n{user}",
            )

            def _invoke() -> LlmCompletion:
                try:
                    response = self._client.converse(
                        modelId=self._model,
                        system=[{"text": system}],
                        messages=[
                            {
                                "role": "user",
                                "content": [{"text": user}],
                            }
                        ],
                        inferenceConfig={
                            "maxTokens": config.max_tokens,
                            "temperature": config.temperature,
                        },
                    )
                except Exception as exc:  # noqa: BLE001
                    raise translate_bedrock_exception(exc) from exc

                output = (
                    response.get("output", {}).get("message", {}).get("content", [])
                )
                texts = [block.get("text", "") for block in output if "text" in block]
                text = "\n".join(t for t in texts if t).strip()
                if not text:
                    raise ProviderError(
                        "Bedrock Converse returned empty text",
                        provider="bedrock",
                        code="EmptyCompletion",
                    )
                return LlmCompletion(
                    text=text,
                    usage=_usage_from_converse(response),
                    provider=self.provider_name,
                    model=self.model_name,
                )

            try:
                completion = await asyncio.to_thread(_invoke)
            except ProviderError as exc:
                set_span_error(span, exc)
                raise
            except Exception as exc:  # noqa: BLE001
                mapped = translate_bedrock_exception(exc)
                set_span_error(span, mapped)
                raise mapped from exc

            usage = completion.usage
            if usage.input_tokens is not None:
                span.set_attribute("llm.usage.input_tokens", usage.input_tokens)
            if usage.output_tokens is not None:
                span.set_attribute("llm.usage.output_tokens", usage.output_tokens)
            set_span_io(span, output=completion.text)
            record_llm_tokens(
                provider=completion.provider,
                model=completion.model,
                purpose="complete",
                input_tokens=usage.input_tokens,
                output_tokens=usage.output_tokens,
            )
            return completion
