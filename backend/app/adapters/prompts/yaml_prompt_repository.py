from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml

from app.domain.llm import LlmInferenceConfig, PromptSpec

DEFAULT_PROMPTS_DIR = Path(__file__).resolve().parents[3] / "prompts"


class YamlPromptRepository:
    """
    Carga prompts desde YAML (estilo prompt-manager liviano).

    Campos soportados:
    - name, description
    - system, user_template
    - max_tokens, temperature
    - empty_reply (opcional, para RAG sin hits)
    """

    def __init__(self, directory: Path | None = None) -> None:
        self._directory = directory or DEFAULT_PROMPTS_DIR

    def get(self, name: str) -> PromptSpec:
        path = self._directory / f"{name}.yaml"
        if not path.exists():
            # también aceptar .yml
            alt = self._directory / f"{name}.yml"
            if not alt.exists():
                raise FileNotFoundError(f"Prompt YAML not found: {path}")
            path = alt
        return _load_prompt_file(path)

    def list_names(self) -> list[str]:
        names = {p.stem for p in self._directory.glob("*.yaml")}
        names |= {p.stem for p in self._directory.glob("*.yml")}
        return sorted(names)


@lru_cache(maxsize=32)
def _load_prompt_file(path: Path) -> PromptSpec:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Prompt YAML must be a mapping: {path}")

    name = str(data.get("name") or path.stem)
    system = data.get("system")
    if not system or not str(system).strip():
        raise ValueError(f"Prompt '{name}' requires non-empty 'system'")

    max_tokens = int(data.get("max_tokens", 256))
    temperature = float(data.get("temperature", 0.0))
    user_template = data.get("user_template")
    empty_reply = data.get("empty_reply")
    description = str(data.get("description") or "")

    return PromptSpec(
        name=name,
        system=str(system).strip(),
        user_template=str(user_template).strip() if user_template else None,
        description=description,
        empty_reply=str(empty_reply).strip() if empty_reply else None,
        config=LlmInferenceConfig(max_tokens=max_tokens, temperature=temperature),
    )


def clear_prompt_cache() -> None:
    _load_prompt_file.cache_clear()
