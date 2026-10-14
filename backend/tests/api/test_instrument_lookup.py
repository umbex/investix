from fastapi.testclient import TestClient

from app.main import create_app
from app.settings import get_settings


def test_instrument_lookup_returns_provider_listings(monkeypatch) -> None:
    monkeypatch.setenv("INVESTIX_DEV_AUTH_BYPASS", "true")
    monkeypatch.setenv("INVESTIX_SESSION_SECRET", "test-session-secret-with-at-least-32chars")
    monkeypatch.setenv("INVESTIX_TWELVE_DATA_API_KEY", "test-key")
    get_settings.cache_clear()
    from app.api import instrument_lookup

    class FakeAdapter:
        def __init__(self, *, api_key: str) -> None:
            assert api_key == "test-key"

        def search_symbols(self, query: str) -> list[dict[str, str]]:
            return [{"symbol": query, "name": "Example ETF", "exchange": "MTA", "currency": "EUR", "type": "ETF"}]

    monkeypatch.setattr(instrument_lookup, "TwelveDataAdapter", FakeAdapter)
    response = TestClient(create_app()).get("/api/instruments/lookup?query=EQQQ")

    assert response.status_code == 200
    assert response.json()["items"][0]["exchange"] == "MTA"
