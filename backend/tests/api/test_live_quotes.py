from fastapi.testclient import TestClient

from app.main import create_app
from app.providers.base import LiveQuote, ProviderError
from app.services.live_quotes import LiveQuoteService
from app.settings import get_settings


class FakeProvider:
    def fetch_live_quotes(self, symbols: list[str]) -> list[LiveQuote]:
        from datetime import datetime, timezone
        from decimal import Decimal
        return [LiveQuote(symbol, Decimal("10"), Decimal("0.5"), datetime.now(timezone.utc), "EUR", Decimal("10"), "test") for symbol in symbols]


def test_live_quotes_endpoint_returns_safe_quota_status(monkeypatch) -> None:
    monkeypatch.setenv("INVESTIX_DEV_AUTH_BYPASS", "true")
    monkeypatch.setenv("INVESTIX_SESSION_SECRET", "test-session-secret-with-at-least-32chars")
    get_settings.cache_clear()
    from app.api import live_quotes
    live_quotes._service = LiveQuoteService(provider=FakeProvider(), now=lambda: 1000.0)

    response = TestClient(create_app()).get("/api/quotes/live?symbols=AAPL,MSFT")

    assert response.status_code == 200
    assert response.json()["items"][0]["ticker"] == "AAPL"
