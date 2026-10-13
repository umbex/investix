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
    twelve_data_api_key: str | None = None
    worker_status_file: str | None = None

    model_config = SettingsConfigDict(env_file=".env", env_prefix="INVESTIX_", extra="ignore")

    @model_validator(mode="after")
    def production_requires_a_session_secret(self) -> "Settings":
        if self.session_secret is None or len(self.session_secret) < 32:
            raise ValueError("INVESTIX_SESSION_SECRET must contain at least 32 characters")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
