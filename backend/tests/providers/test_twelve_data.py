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
