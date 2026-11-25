# Esteban Creaciones — multi-agent RAG chatbot

Hexagonal (ports & adapters) monorepo for a handmade-crafts business chatbot:

- **FAQ RAG** (retrieve + grounded generation)
- **Orders agent** (collect request details → Postgres)
- **Hybrid router**, guardrails, chat history, OpenTelemetry, and a small branded UI

Built to learn and defend clean architecture — not as a rushed MVP.

## Stack

| Layer | Choice |
|-------|--------|
| API | FastAPI + Swagger |
| DB | PostgreSQL + pgvector |
| LLM / embeddings | AWS Bedrock (Nova Lite / Titan) — also `local` / `openai` embeddings |
| Frontend | Vite + React |
| Observability | OpenTelemetry → Jaeger (local, free) |

## Architecture

```
backend/app/
  domain/       # pure models (chat, orders, docs, LLM specs)
  ports/        # interfaces (Embeddings, VectorStore, Agent, Router, Orders…)
  use_cases/    # IngestDocuments, SearchDocuments, HandleChat
  adapters/     # Bedrock, pgvector, agents, router, guardrails, prompts
  api/          # FastAPI composition root + HTTP
  observability/# OTEL setup, spans, payload capture
  eval/         # retrieve quality metrics (no LLM)

frontend/       # chat UI (brand colors, session in localStorage)
backend/prompts/*.yaml   # system/user templates + max_tokens + temperature
```

Use cases depend only on ports — never on Bedrock or SQL drivers directly.

### Chat pipeline

```
POST /chat
  → input guardrail (LLM-as-judge)
  → load history (Postgres + in-memory write-through cache)
  → HybridRouter
  → AgentRegistry[intent]
  → persist turn + return reply + history
```

**Hybrid router**

1. Static intents (greeting / farewell / thanks) → fixed message tuples  
2. Agent keywords (`AGENT_KEYWORDS` in `adapters/router/keywords.py`)  
3. Otherwise → Bedrock classifier (`router_classify.yaml`)

**Agents**

| Intent | Behavior |
|--------|----------|
| `rag` | Retrieve FAQ chunks → quality gate → generate with `rag_answer.yaml` |
| `orders` | Collect **what** / **when** / **phone** → `order_requests` table → confirm we’ll contact them to refine the idea and start work |
| static | Greeting, farewell, thanks, general fallback |

**Prompts** live in `backend/prompts/` with `[[variables]]`, `max_tokens`, `temperature`:

- `input_guardrail_judge.yaml` (48 tokens)
- `router_classify.yaml` (40)
- `rag_answer.yaml` (220)
- `orders_collect.yaml` (280)

**History:** `chat_sessions` / `chat_messages` + RAM cache. Only short windows go to the LLM (`CHAT_HISTORY_WINDOW=6`, `ROUTER_HISTORY_WINDOW=2`). Empty `session_id` creates a new session.

**Guardrails**

- Input: LLM-as-judge; on block → static tuple messages (`adapters/guardrails/static_messages.py`)
- Retrieve: abstain if best score &lt; `RAG_GENERATE_MIN_SCORE` (no generation spend)

**Orders table `order_requests`:** draft → submitted, stores `item_description`, `desired_when`, `contact_phone`, `requested_at`, `submitted_at`, `session_id`.

### Observability (free)

OpenTelemetry SDK → Jaeger all-in-one (no paid SaaS).

- Spans: `chat.handle` → `guardrail.input` → `router.route` → `agent.*` → `llm.complete`
- Each step can expose `input.value` / `output.value` (`OTEL_CAPTURE_PAYLOADS`)
- UI: http://localhost:16686 — service `esteban-creaciones-rag`
- Jaeger is traces-only; OTLP metrics export is disabled for that backend

### Adding another agent

1. Add keywords under `AGENT_KEYWORDS`
2. Implement `AgentPort`
3. Register it in `create_container()` (`app/api/deps.py`)
4. Optionally extend `router_classify.yaml` rules

## Quick start

### 1. Environment

```bash
cp .env.example .env
```

Set Bedrock / AWS profile as needed. Defaults favor Nova Lite for chat, router, and guardrail.

### 2. Infrastructure

```bash
docker compose up postgres jaeger -d
```

### 3. API

```bash
cd backend
python -m venv .venv
# Windows: .\.venv\Scripts\activate
pip install -e ".[bedrock,dev]"   # or .[local,dev] for FastEmbed
uvicorn app.main:app --reload --port 8000
```

Swagger: http://localhost:8000/docs

Suggested order:

1. `POST /rag/ingest` — index `backend/data/faqs/*.md`
2. `POST /rag/search` — debug retrieve
3. `POST /chat` — full pipeline (`session_id: ""` = new session)

### 4. Chat UI

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 (Vite proxies `/chat` to the API).

- Session id is stored in `localStorage`
- **New conversation** (header) clears the session and starts fresh

**Brand:** navy `#1E4E79`, orange `#E65F2B`, amber `#F4C01E`, text `#2C3E50` / white `#FFFFFF`.  
Optional assets (opaque backgrounds OK): `frontend/public/brand/logo.png`, `banner.jpg` — see `frontend/public/brand/README.md`.

## Embedding providers

| `EMBEDDING_PROVIDER` | Cost | Extra install |
|----------------------|------|----------------|
| `local` | Free (CPU, FastEmbed) | `.[local]` |
| `openai` | OpenAI API | included |
| `bedrock` | AWS | `.[bedrock]` |

After changing provider/dimensions, run `POST /rag/ingest` again.

If a stale Hugging Face token breaks `local` downloads, remove `~/.cache/huggingface/token` or set `HF_HUB_DISABLE_IMPLICIT_TOKEN=1`.

## Retrieve evaluation (no LLM)

```bash
cd backend
python -m app.eval.run_retrieve_eval
```

Dataset: `backend/data/evals/retrieve_eval.yaml`

## Tests

```bash
cd backend
pytest -q
```

## Project layout (high level)

```
esteban-creaciones-agent/
  backend/          # FastAPI hexagonal app
  frontend/         # Vite React chat UI
  docker-compose.yml# Postgres + Jaeger (+ optional api service)
  .env.example      # documented settings
  docs/             # extra design notes (English)
```

## Further reading

- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — hexagonal boundaries, chat flow, agents
- [docs/OPERATIONS.md](docs/OPERATIONS.md) — env vars, OTEL, local runbook
