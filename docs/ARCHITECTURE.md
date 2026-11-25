# Architecture

## Goals

- Keep domain logic free of cloud SDKs and frameworks.
- Swap embeddings / LLM / storage behind ports.
- Make every chatbot turn observable and easy to explain in an interview.

## Hexagonal map

| Zone | Responsibility | Examples |
|------|----------------|----------|
| **Domain** | Entities and value objects | `ChatTurn`, `OrderRequest`, `PromptSpec`, `SearchHit` |
| **Ports** | Interfaces the app needs | `LlmPort`, `EmbeddingsPort`, `OrderRequestPort`, `AgentPort` |
| **Use cases** | Application orchestration | `HandleChat`, `SearchDocuments`, `IngestDocuments` |
| **Adapters** | Technology implementations | Bedrock, pgvector, YAML prompts, agents |
| **API** | Composition root + HTTP | `deps.create_container`, FastAPI routes |

Dependency rule: **inward only**. Adapters and API may import domain/ports; domain never imports adapters.

## Chat turn sequence

1. Resolve `session_id` (empty → create; invalid UUID → 400).
2. **Input guardrail** (`LlmJudgeGuardrails`) — block with static copy if unsafe.
3. Load recent history (cache → Postgres).
4. Append user message.
5. **Router** — static / keyword / LLM → intent.
6. **Agent** — produce `AgentReply` + metadata.
7. Append assistant message; return reply, history, sources (RAG), session id.

## Agents

### RAG (`rag`)

1. Embed query and retrieve with min score.
2. Retrieve guardrail (`RAG_GENERATE_MIN_SCORE`).
3. If weak → abstain message (no generation).
4. Else render `rag_answer.yaml` with context + short history → Bedrock.

### Orders (`orders`)

Stateful draft per chat session in `order_requests`:

| Field | Meaning |
|-------|---------|
| `item_description` | What to schedule / commission |
| `desired_when` | Desired date or timeframe (free text) |
| `contact_phone` | Contact number |
| `requested_at` | When the draft was opened |
| `status` | `draft` → `submitted` |

Each turn: LLM extracts updates (`orders_collect.yaml`) → merge draft → if complete, mark submitted and reply that the team will reach out to refine the idea and start work (do not claim the order is “ready”).

### Static

Greeting / farewell / thanks / general: random line from editable tuples.

## Router tie-break

Keyword scores may tie (e.g. “encargar un disfraz”). `orders` wins over `rag` via `_INTENT_TIE_PRIORITY`.

## Prompts as config

YAML next to inference knobs (`max_tokens`, `temperature`) keeps prompt + cost controls together. Runtime placeholders use `[[name]]`.

## Frontend

Thin client: `POST /chat`, keep `session_id` in `localStorage`, render history from the API response. No business logic in the UI.
