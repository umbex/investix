from fastapi.testclient import TestClient
import pytest

from app.main import create_app
from app.settings import get_settings
from app.settings import Settings
from pydantic import ValidationError


def test_portfolio_requires_authenticated_session(monkeypatch) -> None:
    monkeypatch.setenv("INVESTIX_ADMIN_PASSWORD", "test-password")
    monkeypatch.setenv("INVESTIX_SESSION_SECRET", "test-session-secret-with-at-least-32chars")
    get_settings.cache_clear()
    response = TestClient(create_app()).get("/api/portfolio")

    assert response.status_code == 401


def test_configured_credentials_create_a_session(monkeypatch) -> None:
    monkeypatch.setenv("INVESTIX_ADMIN_PASSWORD", "test-password")
    monkeypatch.setenv("INVESTIX_SESSION_SECRET", "test-session-secret-with-at-least-32chars")
    get_settings.cache_clear()
    response = TestClient(create_app()).post(
        "/api/auth/login",
        json={"username": "investix", "password": "test-password"},
    )

    assert response.status_code == 204
    assert "session" in response.cookies


def test_production_rejects_missing_or_short_session_secret() -> None:
    with pytest.raises(ValidationError, match="INVESTIX_SESSION_SECRET"):
        Settings(environment="production", session_secret="short")


def test_settings_ignores_docker_only_environment_variables(monkeypatch) -> None:
    monkeypatch.setenv("POSTGRES_DB", "investix")

    settings = Settings(session_secret="test-session-secret-with-at-least-32chars")

    assert settings.database_url.startswith("postgresql+")


def test_settings_exposes_twelve_data_key_only_server_side(monkeypatch) -> None:
    monkeypatch.setenv("INVESTIX_TWELVE_DATA_API_KEY", "free-test-key")

    settings = Settings(session_secret="test-session-secret-with-at-least-32chars")

    assert settings.twelve_data_api_key == "free-test-key"
