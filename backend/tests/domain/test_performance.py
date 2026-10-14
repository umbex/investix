from datetime import date
from decimal import Decimal

from app.domain.money import normalize_price_to_eur
from app.domain.performance import calculate_cagr, calculate_daily_twr


def test_gbx_is_divided_by_100_before_historical_fx_conversion() -> None:
    assert normalize_price_to_eur(Decimal("250"), "GBX", Decimal("1.17")) == Decimal("2.925")
    assert normalize_price_to_eur(Decimal("2.5"), "GBP", Decimal("1.17")) == Decimal("2.925")


def test_daily_twr_treats_external_flow_as_end_of_day() -> None:
    performance = calculate_daily_twr(
        [
            (date(2026, 1, 1), Decimal("100"), Decimal("0")),
            (date(2026, 1, 2), Decimal("115"), Decimal("10")),
            (date(2026, 1, 3), Decimal("126.5"), Decimal("0")),
        ]
    )

    assert performance.total_return == Decimal("0.155")
    assert performance.days == 2


def test_cagr_is_unavailable_without_positive_start_value_or_elapsed_time() -> None:
    assert calculate_cagr(Decimal("0"), Decimal("120"), 365) is None
    assert calculate_cagr(Decimal("100"), Decimal("120"), 0) is None
    assert calculate_cagr(Decimal("100"), Decimal("121"), 365) == Decimal("0.21")
