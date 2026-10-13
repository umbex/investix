from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Investix"
    environment: str = "development"
    database_url: str = "postgresql+psycopg://investix:investix@db:5432/investix"
    session_secret: str = "change-me-before-production"

    model_config = SettingsConfigDict(env_file=".env", env_prefix="INVESTIX_")


@lru_cache
def get_settings() -> Settings:
    return Settings()
