from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Investix"
    environment: str = "development"
    database_url: str = "postgresql+psycopg://investix:investix@db:5432/investix"
    session_secret: str | None = None
    admin_username: str = "investix"
    admin_password: str | None = None
    dev_auth_bypass: bool = False
    twelve_data_api_key: str | None = None
    worker_status_file: str | None = None
    live_refresh_minutes: int = 5
    live_batch_size: int = 8
    live_credits_per_minute: int = 8
    live_daily_credits: int = 800
    live_daily_reserve_percent: int = 20
    live_session_idle_minutes: int = 10

    model_config = SettingsConfigDict(env_file=".env", env_prefix="INVESTIX_", extra="ignore")

    @model_validator(mode="after")
    def production_requires_a_session_secret(self) -> "Settings":
        if self.session_secret is None or len(self.session_secret) < 32:
            raise ValueError("INVESTIX_SESSION_SECRET must contain at least 32 characters")
        if self.environment.lower() == "production" and self.dev_auth_bypass:
            raise ValueError("INVESTIX_DEV_AUTH_BYPASS cannot be enabled in production")
        if self.live_batch_size < 1 or self.live_batch_size > self.live_credits_per_minute:
            raise ValueError("INVESTIX_LIVE_BATCH_SIZE cannot exceed INVESTIX_LIVE_CREDITS_PER_MINUTE")
        if self.live_refresh_minutes < 1 or self.live_daily_reserve_percent < 0 or self.live_daily_reserve_percent >= 100:
            raise ValueError("Configurazione live quotes non valida")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
