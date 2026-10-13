from datetime import datetime, timezone
from decimal import Decimal

import pytest

from app.providers.base import ProviderError
from app.providers.twelve_data import TwelveDataAdapter


def test_twelve_data_normalizes_latest_eod_quote_and_preserves_source_metadata() -> None:
    adapter = TwelveDataAdapter(
        api_key="test-key",
        download=lambda _: '{"meta":{"symbol":"EQQQ.MI","exchange":"MIL","currency":"EUR"},"values":[{"datetime":"2026-10-12","close":"123.45"}]}'
    )

    quote = adapter.fetch_latest("EQQQ.MI")

    assert quote.ticker == "EQQQ.MI"
    assert quote.raw_price == Decimal("123.45")
    assert quote.currency == "EUR"
    assert quote.observed_at == datetime(2026, 10, 12, tzinfo=timezone.utc)


def test_twelve_data_reports_unknown_symbols_and_rate_limits() -> None:
    unknown = TwelveDataAdapter(api_key="test-key", download=lambda _: '{"code":400,"message":"Invalid symbol"}')
    limited = TwelveDataAdapter(api_key="test-key", download=lambda _: '{"code":429,"message":"API credits exhausted"}')

    with pytest.raises(ProviderError, match="simbolo"):
        unknown.fetch_latest("MISSING")
    with pytest.raises(ProviderError, match="crediti") as error:
        limited.fetch_latest("EQQQ.MI")
    assert error.value.retryable is True
