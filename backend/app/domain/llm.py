from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class LlmInferenceConfig:
    """Parámetros de inferencia. Vienen del YAML del prompt."""

    max_tokens: int = 256
    temperature: float = 0.0


@dataclass(frozen=True, slots=True)
class LlmUsage:
    input_tokens: int | None = None
    output_tokens: int | None = None

    @property
    def total_tokens(self) -> int | None:
        if self.input_tokens is None and self.output_tokens is None:
            return None
        return (self.input_tokens or 0) + (self.output_tokens or 0)

    def to_dict(self) -> dict:
        return {
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.total_tokens,
        }


@dataclass(frozen=True, slots=True)
class LlmCompletion:
    text: str
    usage: LlmUsage
    provider: str
    model: str


@dataclass(frozen=True, slots=True)
class PromptSpec:
    """
    Prompt cargado desde YAML: texto + max_tokens + temperature.

    Variables runtime: [[nombre]] en system / user_template.
    """

    name: str
    system: str
    config: LlmInferenceConfig
    user_template: str | None = None
    description: str = ""
    empty_reply: str | None = None

    def render_system(self, **variables: object) -> str:
        return _render(self.system, variables)

    def render_user(self, **variables: object) -> str:
        if not self.user_template:
            raise ValueError(f"Prompt '{self.name}' has no user_template")
        return _render(self.user_template, variables)


def _render(template: str, variables: dict[str, object]) -> str:
    rendered = template
    for key, value in variables.items():
        rendered = rendered.replace(f"[[{key}]]", str(value))
    return rendered
