from datetime import datetime, timezone
from decimal import Decimal

import pytest

from app.providers.base import MarketObservation, ProviderError, normalize_observation
from app.providers.manual_csv import ManualCsvAdapter


def test_normalizes_gbx_before_fx() -> None:
    observation = normalize_observation(
        provider="manual-csv",
        ticker="VOD.L",
        observed_at=datetime(2026, 1, 2, tzinfo=timezone.utc),
        raw_price=Decimal("250"),
        currency="GBX",
        fx_to_eur=Decimal("1.17"),
    )

    assert observation.normalized_price_eur == Decimal("2.925")
    assert observation.raw_price == Decimal("250")


def test_manual_csv_reads_one_symbol_and_reports_a_missing_one(tmp_path) -> None:
    source = tmp_path / "prices.csv"
    source.write_text("ticker,date,price,currency,fx_to_eur\nVWCE,2026-01-02,100,EUR,1\n")
    adapter = ManualCsvAdapter(source)

    result = adapter.fetch("VWCE")

    assert result.ticker == "VWCE"
    with pytest.raises(ProviderError, match="non trovato"):
        adapter.fetch("MISSING")


def test_invalid_manual_price_is_rejected(tmp_path) -> None:
    source = tmp_path / "prices.csv"
    source.write_text("ticker,date,price,currency,fx_to_eur\nVWCE,2026-01-02,-1,EUR,1\n")

    with pytest.raises(ProviderError, match="prezzo"):
        ManualCsvAdapter(source).fetch("VWCE")


def test_manual_csv_iterates_a_historical_snapshot(tmp_path) -> None:
    source = tmp_path / "prices.csv"
    source.write_text(
        "ticker,date,price,currency,fx_to_eur\n"
        "VWCE,2026-01-02,100,EUR,1\n"
        "VWCE,2026-01-03,101,EUR,1\n"
    )

    observations = list(ManualCsvAdapter(source).iter_observations())

    assert [item.raw_price for item in observations] == [Decimal("100"), Decimal("101")]
    assert observations[-1].observed_at == datetime(2026, 1, 3, tzinfo=timezone.utc)
