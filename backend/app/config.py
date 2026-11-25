from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

EmbeddingProviderName = Literal["local", "openai", "bedrock"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Esteban Creaciones RAG"
    database_url: str = (
        "postgresql+asyncpg://esteban:esteban@localhost:5432/esteban_creaciones"
    )
    # Orígenes del frontend (Vite). Separados por coma.
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    chunk_size: int = 400
    chunk_overlap: int = 80

    retrieve_top_k: int = 5
    retrieve_min_score: float = 0.35
    # Umbral más estricto para GENERAR (si el best score es menor → abstain)
    rag_generate_min_score: float = 0.45
    guardrails_enabled: bool = True

    embedding_provider: EmbeddingProviderName = "local"

    local_embedding_model: str = "BAAI/bge-small-en-v1.5"

    openai_api_key: str = ""
    openai_embedding_model: str = "text-embedding-3-small"
    openai_embedding_dimensions: int = 1536

    aws_region: str = "us-east-1"
    # Perfil SSO/local. Si está vacío, boto3 usa la cadena default
    # (~/.aws/credentials [default]), que a menudo tiene keys viejas.
    aws_profile: str = ""
    bedrock_embedding_model: str = "amazon.titan-embed-text-v2:0"
    bedrock_embedding_dimensions: int = 1024

    # LLMs Bedrock (Converse).
    # Nova Lite: buen equilibrio para RAG/chat. Router/judge: mismo Lite por defecto
    # (JSON corto); si querés aún menos latencia, probá amazon.nova-micro-v1:0 ahí.
    bedrock_router_model: str = "amazon.nova-lite-v1:0"
    bedrock_guardrail_model: str = "amazon.nova-lite-v1:0"
    bedrock_chat_model: str = "amazon.nova-lite-v1:0"
    router_use_llm: bool = True

    # Historial: ventana al LLM (barato) + cache en memoria delante de Postgres
    chat_history_window: int = 6
    router_history_window: int = 2
    chat_history_cache_sessions: int = 256
    chat_history_cache_keep: int = 20

    # OpenTelemetry — SDK + exporters OSS (sin SaaS pago)
    # exporter: none | console | otlp  (otlp → Jaeger local vía OTLP gRPC)
    otel_enabled: bool = False
    otel_exporter: Literal["none", "console", "otlp"] = "otlp"
    otel_service_name: str = "esteban-creaciones-rag"
    otel_environment: str = "local"
    otel_exporter_otlp_endpoint: str = "http://localhost:4317"
    otel_exporter_otlp_insecure: bool = True
    otel_metrics_export_interval_ms: int = 15000
    # Incluir texto de user/assistant en tags del span (útil en local; off en prod)
    otel_capture_payloads: bool = True
    otel_payload_max_chars: int = 1200

    def embedding_dimensions(self) -> int:
        if self.embedding_provider == "openai":
            return self.openai_embedding_dimensions
        if self.embedding_provider == "bedrock":
            return self.bedrock_embedding_dimensions
        # all-MiniLM-L6-v2
        return 384


@lru_cache
def get_settings() -> Settings:
    return Settings()
