from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str = "postgresql+asyncpg://poct:poct@db:5432/poct"

    OPENROUTER_API_KEY: str = ""
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
    LLM_MODEL: str = "google/gemini-3.1-flash-lite"
    OPENROUTER_HTTP_REFERER: str = ""
    OPENROUTER_APP_TITLE: str = "MANA POCT QC Assistant"

    LANGFUSE_PUBLIC_KEY: str = ""
    LANGFUSE_SECRET_KEY: str = ""
    LANGFUSE_HOST: str = "https://cloud.langfuse.com"

    # Event-driven Hard Block dispatch — both are optional fan-out
    # publishers behind the EventPublisher interface; LogPublisher always runs.
    NTFY_TOPIC: str = ""
    NTFY_SERVER: str = "https://ntfy.sh"
    KAFKA_BOOTSTRAP_SERVERS: str = ""
    KAFKA_TOPIC: str = "poct.device.hardblock"
    EVENT_RELAY_INTERVAL_SECONDS: float = 3.0

    DEFAULT_TENANT_ID: str = "demo"

    LOG_LEVEL: str = "INFO"

    # Comma-separated list of allowed frontend origins for CORS. Defaults cover
    # local Docker/Vite dev; in production set this to your deployed frontend
    # URL(s), e.g. "https://my-app.vercel.app".
    CORS_ALLOW_ORIGINS: str = "http://localhost:5173,http://frontend:5173"

    @property
    def cors_allow_origins(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ALLOW_ORIGINS.split(",") if origin.strip()]

    @property
    def has_llm_key(self) -> bool:
        return bool(self.OPENROUTER_API_KEY)

    @property
    def has_langfuse(self) -> bool:
        return bool(self.LANGFUSE_PUBLIC_KEY and self.LANGFUSE_SECRET_KEY)

    @property
    def has_ntfy(self) -> bool:
        return bool(self.NTFY_TOPIC)

    @property
    def has_kafka(self) -> bool:
        return bool(self.KAFKA_BOOTSTRAP_SERVERS)


settings = Settings()
