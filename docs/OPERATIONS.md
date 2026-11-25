# Operations runbook

## Services

| Service | Port | Purpose |
|---------|------|---------|
| FastAPI | 8000 | Chat + RAG API / Swagger |
| Vite UI | 5173 | Chat frontend (proxies API) |
| Postgres | 5432 | History, vectors, order requests |
| Jaeger UI | 16686 | Traces |
| OTLP gRPC | 4317 | Trace export from the API |

```bash
docker compose up postgres jaeger -d
```

## Common env vars

See `.env.example` for the full list. Highlights:

| Variable | Role |
|----------|------|
| `DATABASE_URL` | Async SQLAlchemy URL (`postgresql+asyncpg://…`) |
| `EMBEDDING_PROVIDER` | `local` \| `openai` \| `bedrock` |
| `AWS_PROFILE` / `AWS_REGION` | Bedrock auth (SSO profile recommended) |
| `BEDROCK_CHAT_MODEL` | Generation (default Nova Lite) |
| `BEDROCK_ROUTER_MODEL` | Router classifier |
| `BEDROCK_GUARDRAIL_MODEL` | Input judge |
| `GUARDRAILS_ENABLED` | Toggle LLM judge |
| `RAG_GENERATE_MIN_SCORE` | Min retrieve score to generate |
| `CORS_ORIGINS` | Frontend origins |
| `OTEL_ENABLED` / `OTEL_EXPORTER` | `otlp` \| `console` \| `none` |
| `OTEL_CAPTURE_PAYLOADS` | Attach truncated I/O on spans |

## First-time data

1. Start Postgres.
2. Start API (schema is created on startup: chat tables, `order_requests`, pgvector).
3. `POST /rag/ingest` to load FAQ markdown.

## Debugging a chat turn

1. UI or Swagger `POST /chat`.
2. Jaeger → service `esteban-creaciones-rag` → open the trace.
3. Inspect span tags `input.value` / `output.value` on `chat.handle`, `guardrail.input`, `router.route`, `agent.orders` / `agent.rag`, `llm.complete`.
4. Response `metadata` includes routing, tokens, guardrail codes, orders `collected` flags.

## Tests

```bash
cd backend
pytest -q
```

No live Bedrock/Postgres required for the unit suite (fakes/in-memory doubles).

## Frontend brand assets

Drop files into `frontend/public/brand/`:

- `logo.png` — shown in a white chip (opaque backgrounds OK)
- `banner.jpg` — welcome hero with navy/orange overlay

If missing, the UI falls back to typography only.
