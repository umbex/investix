from datetime import date
from decimal import Decimal

import pytest

from app.providers.base import ProviderError
from app.providers.ecb import EcbUsdEurAdapter


def test_ecb_adapter_converts_usd_per_eur_to_eur_per_usd() -> None:
    adapter = EcbUsdEurAdapter(
        download=lambda _: "TIME_PERIOD,OBS_VALUE\n2026-01-02,1.2500\n2026-01-05,1.2000\n"
    )

    rates = adapter.fetch_rates(date(2026, 1, 2), date(2026, 1, 5))

    assert rates == {
        date(2026, 1, 2): Decimal("0.8"),
        date(2026, 1, 5): Decimal("0.8333333333333333333333333333"),
    }


def test_ecb_adapter_uses_latest_prior_reference_rate_for_non_business_day() -> None:
    adapter = EcbUsdEurAdapter(download=lambda _: "TIME_PERIOD,OBS_VALUE\n2026-01-02,1.25\n")

    rate = adapter.rate_for(date(2026, 1, 4), {date(2026, 1, 2): Decimal("0.8")})

    assert rate == Decimal("0.8")


def test_ecb_adapter_rejects_missing_or_invalid_rows() -> None:
    adapter = EcbUsdEurAdapter(download=lambda _: "TIME_PERIOD,OBS_VALUE\n2026-01-02,0\n")

    with pytest.raises(ProviderError, match="ECB"):
        adapter.fetch_rates(date(2026, 1, 2), date(2026, 1, 2))
