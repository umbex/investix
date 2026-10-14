from datetime import date, datetime, timezone
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

    canonical = adapter.fetch_latest("EQQQ.MI", ticker="EQQQ")
    assert canonical.ticker == "EQQQ"


def test_twelve_data_reports_unknown_symbols_and_rate_limits() -> None:
    unknown = TwelveDataAdapter(api_key="test-key", download=lambda _: '{"code":400,"message":"Invalid symbol"}')
    limited = TwelveDataAdapter(api_key="test-key", download=lambda _: '{"code":429,"message":"API credits exhausted"}')

    with pytest.raises(ProviderError, match="simbolo"):
        unknown.fetch_latest("MISSING")
    with pytest.raises(ProviderError, match="crediti") as error:
        limited.fetch_latest("EQQQ.MI")
    assert error.value.retryable is True


def test_twelve_data_requires_an_explicit_historical_fx_rate_for_non_eur_quotes() -> None:
    payload = '{"meta":{"symbol":"QQQ","exchange":"NASDAQ","currency":"USD"},"values":[{"datetime":"2026-10-12","close":"500"}]}'

    with pytest.raises(ProviderError, match="cambio"):
        TwelveDataAdapter(api_key="test-key", download=lambda _: payload).fetch_latest("QQQ")
    quote = TwelveDataAdapter(api_key="test-key", fx_to_eur=lambda _: Decimal("0.9"), download=lambda _: payload).fetch_latest("QQQ")
    assert quote.normalized_price_eur == Decimal("450.0")


def test_twelve_data_fetches_bounded_history_without_inventing_missing_days() -> None:
    payload = '{"meta":{"symbol":"EQQQ.MI","exchange":"MIL","currency":"EUR"},"values":[{"datetime":"2026-01-06","close":"101"},{"datetime":"2026-01-05","close":"100"}]}'
    adapter = TwelveDataAdapter(api_key="test-key", download=lambda url: payload)

    quotes = list(adapter.fetch_history("EQQQ.MI", ticker="EQQQ", start_date=date(2026, 1, 1), end_date=date(2026, 1, 10)))

    assert [quote.observed_at.date().isoformat() for quote in quotes] == ["2026-01-06", "2026-01-05"]
    assert [quote.raw_price for quote in quotes] == [Decimal("101"), Decimal("100")]


def test_twelve_data_fetches_live_batch_quotes() -> None:
    payload = '{"AAPL":{"symbol":"AAPL","close":"250.10","percent_change":"1.25","datetime":"2026-10-14 15:00:00","currency":"USD"},"MSFT":{"symbol":"MSFT","close":"520.20","percent_change":"-0.50","datetime":"2026-10-14 15:00:00","currency":"USD"}}'
    adapter = TwelveDataAdapter(api_key="test-key", fx_to_eur=lambda _: Decimal("0.9"), download=lambda url: payload)

    quotes = adapter.fetch_live_quotes(["AAPL", "MSFT"])

    assert [quote.ticker for quote in quotes] == ["AAPL", "MSFT"]
    assert quotes[0].price == Decimal("250.10")
    assert quotes[0].change_percent == Decimal("1.25")
    assert quotes[0].currency == "USD"


def test_twelve_data_live_batch_preserves_unknown_symbols_and_quota_state() -> None:
    unknown = TwelveDataAdapter(api_key="test-key", download=lambda _: '{"MISSING":{"code":400,"message":"Invalid symbol"}}')
    with pytest.raises(ProviderError, match="simbolo"):
        unknown.fetch_live_quotes(["MISSING"])

    limited = TwelveDataAdapter(api_key="test-key", download=lambda _: '{"code":429,"message":"API credits exhausted"}')
    with pytest.raises(ProviderError, match="crediti") as error:
        limited.fetch_live_quotes(["AAPL"])
    assert error.value.retryable is True
