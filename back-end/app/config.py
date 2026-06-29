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

    DEFAULT_TENANT_ID: str = "demo"

    LOG_LEVEL: str = "INFO"

    @property
    def has_llm_key(self) -> bool:
        return bool(self.OPENROUTER_API_KEY)

    @property
    def has_langfuse(self) -> bool:
        return bool(self.LANGFUSE_PUBLIC_KEY and self.LANGFUSE_SECRET_KEY)


settings = Settings()
