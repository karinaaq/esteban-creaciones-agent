from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import create_async_engine

from app.adapters.vector_store.pgvector_store import PgVectorStore
from app.api.deps import create_container, set_container
from app.api.routes import router
from app.config import get_settings
from app.observability import setup_observability, shutdown_observability


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    setup_observability(settings, app=app)
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    store = PgVectorStore(engine)
    await store.ensure_schema(settings.embedding_dimensions())
    container = create_container(settings, store, engine)
    await container.history.ensure_schema()
    await container.orders.ensure_schema()
    set_container(container)
    app.state.engine = engine
    app.state.container = container
    try:
        yield
    finally:
        await engine.dispose()
        shutdown_observability()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        description=(
            "Esteban Creaciones — RAG hexagonal + chatbot con router de agentes. "
            "Historial en Postgres + cache en memoria (ventana corta al LLM). "
            "Observabilidad: OpenTelemetry (console/OTLP → Jaeger gratis)."
        ),
        version="0.1.0",
        lifespan=lifespan,
    )
    origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins or ["http://localhost:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(router)
    return app


app = create_app()
