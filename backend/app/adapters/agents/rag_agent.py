from __future__ import annotations

import json

from app.adapters.prompts.yaml_prompt_repository import YamlPromptRepository
from app.domain.chat import AgentReply, ChatTurn, format_history_for_prompt
from app.domain.models import SearchHit
from app.observability import get_tracer, set_span_io
from app.ports.guardrails import GuardrailsPort
from app.ports.llm import LlmPort
from app.use_cases.search_documents import SearchDocuments


def _format_context(hits: list[SearchHit]) -> str:
    blocks: list[str] = []
    for i, hit in enumerate(hits, start=1):
        blocks.append(
            f"[{i}] título={hit.chunk.title} | score={hit.score:.3f}\n"
            f"{hit.chunk.content.strip()}"
        )
    return "\n\n".join(blocks)


class RagAgent:
    """Agente FAQ: retrieve + guardrail de calidad + generación grounded."""

    def __init__(
        self,
        search: SearchDocuments,
        llm: LlmPort,
        prompts: YamlPromptRepository,
        guardrails: GuardrailsPort,
        *,
        prompt_name: str = "rag_answer",
        generate_min_score: float = 0.45,
    ) -> None:
        self._search = search
        self._llm = llm
        self._prompts = prompts
        self._guardrails = guardrails
        self._prompt_name = prompt_name
        self._generate_min_score = generate_min_score

    @property
    def name(self) -> str:
        return "rag"

    async def handle(self, turn: ChatTurn) -> AgentReply:
        with get_tracer().start_as_current_span("agent.rag") as span:
            set_span_io(span, input=turn.message)
            prompt = self._prompts.get(self._prompt_name)

            with get_tracer().start_as_current_span("rag.retrieve") as retrieve_span:
                set_span_io(retrieve_span, input=turn.message)
                result = await self._search.execute(turn.message)
                sources = [
                    {
                        "chunk_id": hit.chunk.chunk_id,
                        "source_id": hit.chunk.source_id,
                        "title": hit.chunk.title,
                        "score": round(hit.score, 4),
                    }
                    for hit in result.hits
                ]
                retrieve_span.set_attribute("rag.hit_count", len(result.hits))
                if result.hits:
                    retrieve_span.set_attribute(
                        "rag.best_score",
                        float(max(h.score for h in result.hits)),
                    )
                set_span_io(
                    retrieve_span,
                    output=json.dumps(sources, ensure_ascii=False),
                )

            history_text = format_history_for_prompt(turn.history)
            span.set_attribute("rag.hit_count", len(result.hits))
            if result.hits:
                span.set_attribute(
                    "rag.best_score",
                    float(max(h.score for h in result.hits)),
                )

            retrieve_gate = self._guardrails.check_retrieve(
                result.hits,
                generate_min_score=self._generate_min_score,
            )
            span.set_attribute("rag.retrieve_verdict", retrieve_gate.verdict)
            span.set_attribute("rag.retrieve_code", retrieve_gate.code or "")
            if not retrieve_gate.allowed:
                text = (
                    prompt.empty_reply
                    if retrieve_gate.code == "no_hits" and prompt.empty_reply
                    else retrieve_gate.message
                )
                span.set_attribute("rag.generated", False)
                set_span_io(
                    span,
                    output=(
                        f"abstain:{retrieve_gate.code} | {text} | "
                        f"sources={json.dumps(sources, ensure_ascii=False)}"
                    ),
                )
                return AgentReply(
                    text=text,
                    intent="rag",
                    agent=self.name,
                    metadata={
                        "sources": sources,
                        "hit_count": len(sources),
                        "generated": False,
                        "guardrail": {
                            "verdict": retrieve_gate.verdict,
                            "code": retrieve_gate.code,
                            "details": retrieve_gate.details,
                        },
                        "prompt": prompt.name,
                        "history_messages": len(turn.history),
                        "generate_min_score": self._generate_min_score,
                    },
                )

            context = _format_context(result.hits)
            system = prompt.render_system(context=context, chat_history=history_text)
            user = prompt.render_user(question=turn.message, chat_history=history_text)
            completion = await self._llm.complete(
                system=system,
                user=user,
                config=prompt.config,
            )
            span.set_attribute("rag.generated", True)
            set_span_io(span, output=completion.text)

            return AgentReply(
                text=completion.text,
                intent="rag",
                agent=self.name,
                metadata={
                    "sources": sources,
                    "hit_count": len(sources),
                    "generated": True,
                    "guardrail": {
                        "verdict": retrieve_gate.verdict,
                        "code": retrieve_gate.code,
                        "details": retrieve_gate.details,
                    },
                    "prompt": prompt.name,
                    "history_messages": len(turn.history),
                    "generate_min_score": self._generate_min_score,
                    "embedding_provider": result.provider,
                    "embedding_model": result.model,
                    "llm_provider": completion.provider,
                    "llm_model": completion.model,
                    "llm_tokens": completion.usage.to_dict(),
                },
            )
