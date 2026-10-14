from datetime import datetime, timezone
from decimal import Decimal

from app.providers.base import LiveQuote, ProviderError
from app.services.live_quotes import LiveQuoteService


class FakeProvider:
    def __init__(self, *, limited: bool = False) -> None:
        self.calls: list[list[str]] = []
        self.limited = limited

    def fetch_live_quotes(self, symbols: list[str]) -> list[LiveQuote]:
        self.calls.append(symbols)
        if self.limited:
            raise ProviderError("crediti esauriti", retryable=True)
        now = datetime(2026, 10, 14, 12, 0, tzinfo=timezone.utc)
        return [LiveQuote(s, Decimal("100"), Decimal("1"), now, "EUR", Decimal("100"), "test") for s in symbols]


def test_live_service_splits_symbols_and_defers_second_batch_until_next_window() -> None:
    provider = FakeProvider()
    clock = [1_000.0]
    service = LiveQuoteService(provider=provider, batch_size=8, credits_per_minute=8, daily_credits=800, daily_reserve_percent=20, now=lambda: clock[0])
    first = service.get_snapshot([f"T{i}" for i in range(15)], session_id="tab")
    second = service.get_snapshot([f"T{i}" for i in range(15)], session_id="tab")
    assert provider.calls == [[f"T{i}" for i in range(8)]]
    assert first["statuses"]["T14"] == "pending"
    assert second["statuses"]["T14"] == "pending"
    clock[0] += 60
    service.get_snapshot([f"T{i}" for i in range(15)], session_id="tab")
    assert provider.calls == [[f"T{i}" for i in range(8)], [f"T{i}" for i in range(8, 15)]]


def test_live_service_quota_exhaustion_is_a_safe_status() -> None:
    service = LiveQuoteService(provider=FakeProvider(limited=True), batch_size=8, credits_per_minute=8, daily_credits=800, daily_reserve_percent=20, now=lambda: 1_000.0)
    snapshot = service.get_snapshot(["AAPL"], session_id="tab")
    assert snapshot["status"] == "quota_exhausted"
    assert snapshot["items"] == []
    assert snapshot["retry_after"] > 1_000.0
